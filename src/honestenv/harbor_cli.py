import subprocess
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
