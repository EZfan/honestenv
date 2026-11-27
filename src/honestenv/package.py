from pathlib import Path

from .types import TaskPackage


def load(path: Path) -> TaskPackage:
    raise NotImplementedError


def content_hash(package: TaskPackage) -> str:
    raise NotImplementedError
