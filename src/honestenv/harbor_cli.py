from pathlib import Path

from .types import CommandResult


def lint(task_dir: Path, *, extend_select_all: bool = True) -> CommandResult:
    raise NotImplementedError
