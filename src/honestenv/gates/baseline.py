"""Static factory policy checks independent of Harbor.

Headroom Policy: verifier.timeout_sec must be finite, positive, and at least
15 seconds. When metadata.expected_oracle_runtime_sec is finite and positive,
the timeout must also be at least three times that expected runtime.
"""

import ipaddress
import math
import re
import tomllib
from urllib.parse import urlsplit

from ..types import GateReport, TaskPackage


PIN = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
REWARD_ONE = re.compile(r"\b(?:echo\s+['\"]?1(?:\.0+)?['\"]?|printf\s+['\"]?1(?:\.0+)?(?:\\n)?['\"]?)\s*(?:>|\|)")


def check_baseline(package: TaskPackage, profile: str = "factory") -> GateReport:
    if profile == "audit":
        return _check_audit(package)
    if profile != "factory":
        raise ValueError(f"Unknown profile: {profile}")
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
    references_artifact = any(isinstance(item, str) and (item in script or item.rsplit("/", 1)[-1].removesuffix(".py") in script) for item in artifacts)
    if not rewards:
        violations.append("reward: no reward 1 write found")
    else:
        for reward in rewards:
            before = script[:reward.start()]
            condition = re.search(r"\bif\b((?:(?!\bfi\b).)*?)\bthen\b(?:(?!\b(?:fi|else|elif)\b).)*$", before, re.S)
            if not condition or not any(isinstance(item, str) and (item in condition.group(1) or item.rsplit("/", 1)[-1].removesuffix(".py") in condition.group(1)) for item in artifacts):
                violations.append("reward: reward 1 is not conditional on a check of a packaged artifact")
            if re.search(r"\bexit\s+[1-9][0-9]*\b", script[reward.end():]):
                violations.append("reward: reward 1 can be followed by a non-zero exit")
    if not references_artifact:
        violations.append("reward: test does not reference a packaged artifact")
    if re.search(r"\$\{?RANDOM\}?|/dev/(?:u?random)|\b(?:import random|from random import|random\.)|\b(?:date|time\.time|datetime\.now)\b", script):
        violations.append("reward: nondeterministic test material")

    return GateReport("factory", not violations, "; ".join(violations) if violations else "Factory policy checks passed")


def _check_audit(package: TaskPackage) -> GateReport:
    factory = check_baseline(package)
    policy = factory.details if not factory.passed else "Factory policy checks passed"
    try:
        script = (package.root / "tests/test.sh").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return GateReport("audit", False, f"reward: cannot read tests/test.sh; factory policy: {policy}")

    executable = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    failures = []
    if "test-network: tests/test.sh fetches a public host" in policy:
        failures.append("test-network: tests/test.sh fetches a public host")

    rewards = list(REWARD_ONE.finditer(executable))
    if re.search(r"write_reward\s*\(\s*\)\s*\{[^}]*reward\.txt", executable, re.S):
        rewards += list(re.finditer(r"\bwrite_reward\s+1\b", executable))
    delegated = False
    for name in re.findall(r"(?:/tests/|tests/)(verify\.py|checks\.py)\b", executable):
        try:
            source = (package.root / "tests" / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if re.search(r"\b(?:import rewardkit|from rewardkit import)\b", source) and re.search(r"\b(?:run|rk\.run)\s*\(", source):
            delegated = True
    delegated |= bool(re.search(r"\bpython(?:3|[0-9.]*)?\s+(?:-\S+\s+)*-m\s+rewardkit\b", executable))
    if not rewards and not delegated:
        failures.append("reward: no recognizable reward-producing check found")
    for reward in rewards:
        before = executable[:reward.start()]
        condition = re.search(r"\bif\b((?:(?!\bfi\b).)*?)\bthen\b(?:(?!\b(?:fi|else|elif)\b).)*$", before, re.S)
        success = condition and not re.search(r"(?:\bif\s+!|\s-(?:ne|gt)\s*0\b|!=\s*0)", condition.group(0))
        if success:
            expression = condition.group(1)
            status = re.search(r'\$\{?([A-Za-z_][A-Za-z_0-9]*|\?)\}?', expression)
            direct_check = re.search(r"\b(?:pytest|python[0-9.]*|test|cmp|node|playwright)\b", expression)
            status_check = status and (status.group(1) == "?" or re.search(r"\b" + re.escape(status.group(1)) + r"=\$\?", before, re.I))
            success = direct_check or status_check
        if not success:
            failures.append("reward: reward 1 is unconditional or follows a failed test")
        after = executable[reward.end():]
        after = re.sub(r"^((?:(?!\b(?:else|fi)\b).)*?)\belse\b.*?\bfi\b", r"\1", after, count=1, flags=re.S)
        if re.search(r"\bexit\s+[1-9][0-9]*\b", after):
            failures.append("reward: reward 1 can be followed by a non-zero exit")
    if re.search(r"\$\{?RANDOM\}?|/dev/(?:u?random)|\b(?:import random|from random import|random\.)|\b(?:date|time\.time|datetime\.now)\b", script):
        failures.append("reward: nondeterministic test material")
    details = "; ".join(failures) if failures else "Audit integrity checks passed"
    return GateReport("audit", not failures, f"{details}; factory policy: {policy}")
