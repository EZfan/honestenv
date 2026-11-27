import hashlib
from pathlib import Path

from .types import TaskPackage


def load(path: Path) -> TaskPackage:
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)

    package = TaskPackage(root=root, content_hash="")
    package.content_hash = content_hash(package)
    return package


def content_hash(package: TaskPackage) -> str:
    digest = hashlib.sha256()
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
