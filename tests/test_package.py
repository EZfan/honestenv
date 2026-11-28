import tempfile
import unittest
from pathlib import Path

from honestenv.package import content_hash, load
from honestenv.types import TaskPackage


class PackageTest(unittest.TestCase):
    def test_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "task.toml").write_bytes(b"task")

            package = load(root / "nested" / "..")

            self.assertIsInstance(package, TaskPackage)
            self.assertEqual(package.root, root.resolve())
            self.assertEqual(package.content_hash, content_hash(package))
            self.assertRegex(package.content_hash, r"^[0-9a-f]{64}$")

    def test_load_requires_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file_path = root / "task.toml"
            file_path.touch()

            with self.assertRaises(FileNotFoundError):
                load(root / "missing")
            with self.assertRaises(NotADirectoryError):
                load(file_path)

    def test_rejects_symbolic_links_and_special_files(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "link").symlink_to("/etc/passwd")
            with self.assertRaises(ValueError):
                load(root)
            (root / "link").unlink()
            os.mkfifo(root / "pipe")
            with self.assertRaises(ValueError):
                load(root)

    def test_content_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root = Path(first)
            second_root = Path(second)
            files = {"task.toml": b"task", "nested/data.bin": b"\x00\xff"}
            for root, entries in (
                (first_root, files.items()),
                (second_root, reversed(list(files.items()))),
            ):
                for relative_path, data in entries:
                    path = root / relative_path
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)

            first_package = load(first_root)
            second_package = load(second_root)
            self.assertEqual(content_hash(first_package), first_package.content_hash)
            self.assertEqual(first_package.content_hash, second_package.content_hash)

    def test_content_hash_changes_when_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "task.toml"
            path.write_bytes(b"first")
            package = load(root)

            path.write_bytes(b"other")
            changed_hash = content_hash(package)
            self.assertNotEqual(package.content_hash, changed_hash)
            self.assertEqual(load(root).content_hash, changed_hash)

            path.rename(root / "renamed.toml")
            self.assertNotEqual(changed_hash, content_hash(package))
