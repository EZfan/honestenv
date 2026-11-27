import os
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from honestenv.cli import run


class InitTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        old_cwd = Path.cwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, old_cwd)

    def run_cli(self, *args):
        with patch("sys.argv", ["honestenv", *map(str, args)]):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
                result = run()
        return result, errors.getvalue()

    def test_init_creates_static_checkable_task(self):
        self.assertEqual(self.run_cli("init", "org/example")[0], 0)
        task = Path("tasks/example")
        with (task / "task.toml").open("rb") as config:
            self.assertEqual(tomllib.load(config)["task"]["name"], "org/example")
        for name in ("instruction.md", "environment/Dockerfile", "tests/Dockerfile", "tests/test.sh", "solution/solve.sh"):
            self.assertTrue((task / name).is_file(), name)
        for name in ("tests/test.sh", "solution/solve.sh"):
            self.assertEqual((task / name).stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.run_cli("check", task, "--static-only")[0], 0)

    def test_invalid_names(self):
        for name in ("task", "/task", "org/", "org/a/b", "org/..", "org/."):
            with self.subTest(name=name):
                result, error = self.run_cli("init", name)
                self.assertNotEqual(result, 0)
                self.assertTrue(error.strip())
        self.assertFalse(Path("tasks").exists())

    def test_overwrite_requires_force_and_empty_directory_is_allowed(self):
        task = Path("tasks/example")
        task.mkdir(parents=True)
        self.assertEqual(self.run_cli("init", "org/example")[0], 0)
        instruction = task / "instruction.md"
        instruction.write_text("Keep this.\n", encoding="utf-8")
        result, error = self.run_cli("init", "org/example")
        self.assertNotEqual(result, 0)
        self.assertTrue(error.strip())
        self.assertEqual(instruction.read_text(encoding="utf-8"), "Keep this.\n")
        self.assertEqual(self.run_cli("init", "org/example", "--force")[0], 0)
        self.assertNotEqual(instruction.read_text(encoding="utf-8"), "Keep this.\n")
        self.assertEqual(self.run_cli("check", task, "--static-only")[0], 0)


if __name__ == "__main__":
    unittest.main()
