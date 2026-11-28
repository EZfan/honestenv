"""Load tasks and hash their files.

SHA-256 covers files in sorted relative POSIX path order. For each file, the
UTF-8 path and file bytes are each preceded by their 8-byte big-endian length.
The recorded digest is lowercase hexadecimal.
"""
import hashlib
import os
import stat
from pathlib import Path

from .types import TaskPackage


def load(path: Path) -> TaskPackage:
    if path.is_symlink():
        raise ValueError(f"unsupported symbolic link: {path}")
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)

    package = TaskPackage(root=root, content_hash="")
    package.content_hash = content_hash(package)
    return package


def content_hash(package: TaskPackage) -> str:
    digest = hashlib.sha256()
    for root, directories, files in os.walk(package.root, followlinks=False):
        for name in directories + files:
            path = Path(root) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError(f"unsupported file type: {path}")
    relative_paths = sorted(
        path.relative_to(package.root).as_posix()
        for path in package.root.rglob("*")
        if path.is_file()
    )
    for relative_path in relative_paths:
        path_bytes = relative_path.encode("utf-8")
        file_bytes = (package.root / relative_path).read_bytes()
        # Length prefixes keep paths and file contents unambiguous.
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(len(file_bytes).to_bytes(8, "big"))
        digest.update(file_bytes)
    return digest.hexdigest()


def permissions(package: TaskPackage) -> tuple[tuple[str, int], ...]:
    """Return ordinary permission bits for the validated tree."""
    content_hash(package)
    return tuple(sorted(
        (path.relative_to(package.root).as_posix(), stat.S_IMODE(path.lstat().st_mode))
        for path in (package.root, *package.root.rglob("*"))
    ))
