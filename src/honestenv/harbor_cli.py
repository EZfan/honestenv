import json
import math
import subprocess
import tempfile
from pathlib import Path

from .types import CommandResult


def lint(task_dir: Path, *, extend_select_all: bool = True) -> CommandResult:
    argv = ["harbor", "lint"]
    if extend_select_all:
        argv.extend(["--extend-select", "ALL"])
    argv.append(str(task_dir))

    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    return CommandResult(
        argv=argv,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def read_reward(jobs_dir: Path) -> float | int | None:
    # Harbor 0.27.0 persists individual trial results separately from job summaries.
    result_paths = list(jobs_dir.glob("*/*/result.json"))
    if len(result_paths) != 1:
        return None
    try:
        result = json.loads(result_paths[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(result, dict) or result.get("reward_valid") is not True:
        return None
    verifier = result.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    reward = rewards.get("reward") if isinstance(rewards, dict) else None
    if type(reward) is int or (type(reward) is float and math.isfinite(reward)):
        return reward
    return None


def run(task_dir: Path, *, agent: str) -> CommandResult:
    with tempfile.TemporaryDirectory(prefix="honestenv-jobs-") as directory:
        argv = [
            "harbor", "run", "-p", str(task_dir), "-a", agent, "-e", "docker",
            "--jobs-dir", directory, "--yes",
        ]
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        return CommandResult(
            argv=argv,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            reward=read_reward(Path(directory)),
        )
