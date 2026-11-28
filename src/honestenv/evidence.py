"""Retain an explicitly selected Harbor task and replay one case."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import __version__
from .case_schema import BinaryProfile, Case, Report, Run, record_reward
from .package import load
from .harbor_cli import read_reward

_SENSITIVE_NAME = re.compile(r'(?i)(^\.env($|\.)|(^|[._-])(credential|credentials|secret|secrets|token|tokens|private[_-]?key)([._-]|$)|\.(pem|key|p12|pfx)$)')
_SENSITIVE_VALUE = re.compile(rb'(?i)(?:\b(?:[a-z0-9]*[_-])*(?:api[_-]?key|access[_-]?key(?:[_-]?id)?|access[_-]?token|auth(?:orization)?|password|passwd|secret(?:[_-]?access[_-]?key)?|credential|private[_-]?key|token)\b["\']?\s*[:=]\s*["\']?[^\s"\']+|\bBearer\s+[A-Za-z0-9._~+/-]+|-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{12,})')


def _check_bytes(data: bytes) -> None:
    if _SENSITIVE_VALUE.search(data):
        raise ValueError("sensitive content detected; evidence was not retained")


def _check_tree(root: Path) -> None:
    load(root)
    for path in root.rglob("*"):
        if _SENSITIVE_NAME.search(path.name):
            raise ValueError("sensitive filename detected; evidence was not retained")
        if path.is_file():
            _check_bytes(path.read_bytes())


def _trial(jobs: Path) -> dict:
    paths = list(jobs.glob("*/*/result.json"))
    if len(paths) != 1:
        return {}
    try:
        result = json.loads(paths[0].read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def run_case(task: Path, destination: Path, *, agent: str, expected: str,
             confirmed_defect: bool = False) -> bool:
    """Execute one explicit task and retain failing or confirmed-defect runs."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if agent not in ("oracle", "nop") or expected not in ("must_pass", "must_fail", "unknown"):
        raise ValueError("unsupported agent or expected label")
    _check_tree(task)
    if destination.resolve().is_relative_to(task.resolve()):
        raise ValueError("evidence destination must be outside the task")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".honestenv-evidence-", dir=destination.parent) as staging:
        stage = Path(staging)
        snapshot = stage / "task"
        shutil.copytree(task, snapshot, symlinks=True)
        _check_tree(snapshot)
        digest = load(snapshot).content_hash
        spec = snapshot / "task.toml"
        spec_digest = hashlib.sha256(spec.read_bytes()).hexdigest()
        case = Case("case", "1", "task", digest, "task/task.toml", spec_digest,
                    ("task",), expected, "caller-provided")
        profile = BinaryProfile("binary-v1", 1, 0)
        with tempfile.TemporaryDirectory(prefix="honestenv-jobs-") as jobs:
            command = ["harbor", "run", "-p", str(snapshot), "-a", agent, "-e", "docker", "--jobs-dir", jobs, "--yes"]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            trial = _trial(Path(jobs))
        if load(snapshot).content_hash != digest:
            raise ValueError("task snapshot changed during execution")
        try:
            version = subprocess.run(["harbor", "--version"], capture_output=True, text=True, check=False)
            harbor_version = version.stdout.strip() if version.returncode == 0 else "unknown"
        except OSError:
            harbor_version = "unknown"
        harbor_version = harbor_version or "unknown"
        if result.returncode:
            recorded = record_reward(case, profile, trial, harbor_version=harbor_version,
                                     honestenv_version=__version__)
            run = Run(case, profile, "execution_error", None, recorded.reward_raw, False,
                      "harbor_nonzero_exit", harbor_version, __version__, ("stdout.txt", "stderr.txt"))
        else:
            run = record_reward(case, profile, trial, harbor_version=harbor_version,
                                honestenv_version=__version__, evidence_refs=("stdout.txt", "stderr.txt"))
        failed = run.run_status != "graded" or (expected != "unknown" and run.conclusion != {"must_pass": "pass", "must_fail": "fail"}[expected])
        if not failed and not confirmed_defect:
            return False
        # Free-form streams can contain secrets, so reject rather than persist matches.
        for name, content in (("stdout.txt", result.stdout), ("stderr.txt", result.stderr)):
            _check_bytes(content.encode())
            (stage / name).write_text(content, encoding="utf-8")
        report = Report((run,)).to_json()
        _check_bytes(report.encode())
        (stage / "report.json").write_text(report + "\n", encoding="utf-8")
        (stage / "replay.json").write_text(json.dumps({"version": 1, "agent": agent, "task_hash": digest}) + "\n")
        os.rename(stage, destination)
    return True


def replay(pack: Path) -> int:
    """Replay the bundled task without consulting its original location."""
    metadata = json.loads((pack / "replay.json").read_text(encoding="utf-8"))
    if set(metadata) != {"version", "agent", "task_hash"} or metadata["version"] != 1 or metadata["agent"] not in ("oracle", "nop"):
        raise ValueError("invalid replay metadata")
    task = pack / "task"
    _check_tree(task)
    if load(task).content_hash != metadata["task_hash"]:
        raise ValueError("task snapshot changed")
    with tempfile.TemporaryDirectory(prefix="honestenv-replay-") as jobs:
        result = subprocess.run(["harbor", "run", "-p", str(task.resolve()), "-a", metadata["agent"],
                                 "-e", "docker", "--jobs-dir", jobs, "--yes"], check=False)
        reward = read_reward(Path(jobs))
        print(f"Replay reward: {reward}")
        return result.returncode if result.returncode else (0 if reward is not None else 1)
