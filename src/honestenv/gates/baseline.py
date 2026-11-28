"""Static factory policy checks independent of Harbor.

Headroom Policy: verifier.timeout_sec must be finite, positive, and at least
15 seconds. When metadata.expected_oracle_runtime_sec is finite and positive,
the timeout must also be at least three times that expected runtime.
"""

import ipaddress
import ast
import math
import re
import shlex
import tomllib
from urllib.parse import urlsplit

from ..types import GateReport, TaskPackage
from .python_verifier import python_verifier_warnings


PIN = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
REWARD_ONE = re.compile(r"\b(?:echo\s+['\"]?1(?:\.0+)?['\"]?|printf\s+['\"]?1(?:\.0+)?(?:\\n)?['\"]?)\s*(?:>|\|)")


def delegated_verifier(root, script, artifacts):
    for line in script.splitlines():
        if line.lstrip().startswith('#'):
            continue
        match = re.search(r"\bpython(?:3(?:\.\d+)?)?\s+(?:-\w+\s+)*(?:/tests/|tests/|\./)([\w.-]+\.py)(?:\s|;|$)", line)
        if not match:
            continue
        try:
            source = (root / 'tests' / match.group(1)).read_text(encoding='utf-8')
            tree = ast.parse(source)
        except (OSError, UnicodeError, SyntaxError):
            continue
        # Require an actual write call, a reward path, a value of one, and
        # some conditional logic referencing the packaged artifact.
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        writes = any(isinstance(call.func, ast.Attribute) and call.func.attr in {'write', 'write_text'} and call.args and isinstance(call.args[0], ast.Constant) and str(call.args[0].value).strip() in {'1', '1.0'} for call in calls)
        if writes and '/logs/verifier/reward.txt' in source and any(isinstance(node, (ast.If, ast.IfExp, ast.Assert)) for node in ast.walk(tree)) and any(isinstance(item, str) and (item in source or item.rsplit('/', 1)[-1].removesuffix('.py') in source) for item in artifacts):
            return True
    return False


def grep_warnings(script, artifacts):
    warnings = []
    for number, line in enumerate(script.splitlines(), 1):
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars=';|&<>')
            lexer.whitespace_split = True
            words = list(lexer)
        except ValueError:
            continue
        for i, word in enumerate(words):
            if word != 'grep':
                continue
            args = []
            for arg in words[i + 1:]:
                if arg in {';', '|', '&&', '||', ')'}:
                    break
                args.append(arg)
            if not any(item in args for item in artifacts if isinstance(item, str)):
                continue
            options = [arg for arg in args if arg.startswith('-')]
            positional = [arg for arg in args if not arg.startswith('-')]
            if not positional:
                continue
            pattern = positional[0]
            if '--line-regexp' in options or any(not opt.startswith('--') and 'x' in opt[1:] for opt in options) or (pattern.startswith('^') and pattern.endswith('$')):
                continue
            warnings.append(f"HE-004: tests/test.sh:{number}: grep uses an unanchored pattern on a packaged artifact; use -Fx or ^...$")
    return warnings


def check_baseline(package: TaskPackage) -> GateReport:
    violations = []
    try:
        with (package.root / "task.toml").open("rb") as task_file:
            config = tomllib.load(task_file)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return GateReport("factory", False, "Cannot parse task.toml")

    def table(name):
        value = config.get(name, {})
        return value if isinstance(value, dict) else {}

    environment = table("environment")
    agent = table("agent")
    verifier = table("verifier")
    metadata = table("metadata")
    image = environment.get("docker_image")
    if image is not None and (not isinstance(image, str) or not PIN.search(image) or image.startswith("@")):
        violations.append("image: environment.docker_image must be digest-pinned")

    dockerfiles = []
    for name in ("environment/Dockerfile", "tests/Dockerfile"):
        path = package.root / name
        if not path.is_file():
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            violations.append(f"image: cannot read {name}")
            continue
        dockerfiles.append((name, contents))
        stages = set()
        for line in contents.splitlines():
            match = re.match(r"\s*FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
            if match:
                reference, stage = match.groups()
                if reference.lower() != "scratch" and reference.lower() not in stages and (not PIN.search(reference) or reference.startswith("@")):
                    violations.append(f"image: {name} FROM {reference} must be digest-pinned")
                if stage:
                    stages.add(stage.lower())
        if re.search(r"--network(?:=|\s+)host\b", contents, re.I):
            violations.append(f"network: {name} uses host networking")

    if verifier.get("environment_mode") != "separate":
        violations.append('verifier: environment_mode must be explicitly "separate"')
    mode = agent.get("network_mode", environment.get("network_mode", "public"))
    if mode == "allowlist":
        hosts = environment.get("allowed_hosts")
        if not isinstance(hosts, list) or not hosts or any(not isinstance(host, str) or not host.strip() or host.strip() in {"*", "0.0.0.0/0", "::/0"} for host in hosts):
            violations.append("network: allowlist must contain restricted allowed_hosts")
    elif mode != "no-network":
        violations.append("network: effective agent policy must be restricted")

    def positive_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

    timeout = verifier.get("timeout_sec")
    expected = metadata.get("expected_oracle_runtime_sec")
    if not positive_number(timeout) or timeout < 15:
        violations.append("headroom: verifier.timeout_sec must be finite and at least 15 seconds")
    elif positive_number(expected) and timeout < 3 * expected:
        violations.append("headroom: verifier.timeout_sec must be at least three times expected oracle runtime")

    user = agent.get("user")
    if not isinstance(user, (str, int)) or isinstance(user, bool) or str(user).strip().lower() in {"", "root", "0"}:
        violations.append("agent: user must be present and non-root")

    script_path = package.root / "tests/test.sh"
    try:
        script = script_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        script = ""
        violations.append("reward: cannot read tests/test.sh")

    for name, contents in dockerfiles + [("tests/test.sh", script)]:
        for line in contents.splitlines():
            if line.lstrip().startswith("#") or not re.search(r"\b(?:curl|wget|git\s+clone|fetch|httpie)\b", line, re.I):
                continue
            urls = re.findall(r"(?:https?|git|ssh)://[^\s'\";]+", line, re.I)
            for url in urls:
                host = urlsplit(url).hostname
                try:
                    local = host is not None and ipaddress.ip_address(host).is_loopback
                except ValueError:
                    local = host is not None and host.lower() == "localhost"
                if not local:
                    violations.append(f"test-network: {name} fetches a public host")
            if not urls:
                target = re.search(r"\b(?:curl|wget|fetch|httpie|git\s+clone)\s+(?:-\S+\s+)*([^\s;]+)", line, re.I)
                if target:
                    host = target.group(1).split("/", 1)[0].split(":", 1)[0].split("@")[-1]
                    try:
                        local = ipaddress.ip_address(host.strip("[]")).is_loopback
                    except ValueError:
                        local = host.lower() == "localhost"
                    if not local:
                        violations.append(f"test-network: {name} fetches a public host")

    rewards = list(REWARD_ONE.finditer(script))
    artifacts = config.get("artifacts", [])
    artifacts = artifacts if isinstance(artifacts, list) else []
    violations.extend(grep_warnings(script, artifacts))
    violations.extend(python_verifier_warnings(package.root))
    delegated = delegated_verifier(package.root, script, artifacts)
    references_artifact = any(isinstance(item, str) and (item in script or item.rsplit("/", 1)[-1].removesuffix(".py") in script) for item in artifacts)
    if not rewards and not delegated:
        violations.append("reward: no reward 1 write found")
    elif rewards:
        for reward in rewards:
            before = script[:reward.start()]
            condition = re.search(r"\bif\b((?:(?!\bfi\b).)*?)\bthen\b(?:(?!\b(?:fi|else|elif)\b).)*$", before, re.S)
            if not condition or not any(isinstance(item, str) and (item in condition.group(1) or item.rsplit("/", 1)[-1].removesuffix(".py") in condition.group(1)) for item in artifacts):
                violations.append("reward: reward 1 is not conditional on a check of a packaged artifact")
            if re.search(r"\bexit\s+[1-9][0-9]*\b", script[reward.end():]):
                violations.append("reward: reward 1 can be followed by a non-zero exit")
    if not references_artifact and not delegated:
        violations.append("reward: test does not reference a packaged artifact")
    if re.search(r"\$\{?RANDOM\}?|/dev/(?:u?random)|\b(?:import random|from random import|random\.)|\b(?:date|time\.time|datetime\.now)\b", script):
        violations.append("reward: nondeterministic test material")

    return GateReport("factory", not violations, "; ".join(violations) if violations else "Factory policy checks passed")
