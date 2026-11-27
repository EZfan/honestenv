import importlib.util
import json
import os
import subprocess
import tempfile
from unittest.mock import patch
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "ci_checkup", Path(__file__).resolve().parents[1] / ".github/actions/runtime/checkup.py"
)
checkup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkup)


class RuntimePlannerTests(unittest.TestCase):
    def test_selects_changed_shipped_tasks_only(self):
        self.assertEqual(
            checkup.select_runtime(["tasks/b/file", "tasks/unknown/file", "tests/fixtures/bad_tasks/a/file"], ["a", "b"]),
            ["b"],
        )

    def test_shared_gate_changes_select_all(self):
        for path in ["src/honestenv/cli.py", "pyproject.toml", ".github/workflows/ci.yml", ".github/actions/test/action.yml"]:
            with self.subTest(path=path):
                self.assertEqual(checkup.select_runtime([path], ["b", "a"]), ["a", "b"])

    def test_non_gating_changes_skip_runtime(self):
        self.assertEqual(checkup.select_runtime(["README.md", "CHANGELOG.md", "LICENSE", "CONTRIBUTING.md"], ["a", "b"]), [])

    def test_deleted_task_is_not_selected(self):
        self.assertEqual(checkup.select_runtime(["tasks/deleted/task.toml"], ["a"]), [])


class CheckupTests(unittest.TestCase):
    def test_pull_request_diff_uses_merge_base(self):
        self.assertEqual(
            checkup.diff_command("base-sha"),
            ["git", "diff", "--no-renames", "--name-only", "-z", "base-sha...HEAD"],
        )

    def test_missing_report_does_not_reuse_previous_task_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("a", "b"):
                task = root / "tasks" / name
                task.mkdir(parents=True)
                (task / "task.toml").touch()
            output = root / "checkup.md"
            gates = [{"name": name, "passed": True} for name in ("schema", "lint", "factory", "oracle", "nop")]

            def run(command, **kwargs):
                if command[2] == "tasks/a":
                    Path(command[4]).write_text(json.dumps({"gates": gates}))
                    return subprocess.CompletedProcess(command, 0)
                return subprocess.CompletedProcess(command, 1)

            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"EVENT_NAME": "push", "REPORT_PATH": str(output)}), \
                        patch.object(checkup.subprocess, "run", side_effect=run):
                    self.assertEqual(checkup.main(), 1)
            finally:
                os.chdir(previous)
            content = output.read_text()
            self.assertIn("| a | passed | passed | passed | passed |", content)
            self.assertIn("| b | failed | failed | failed | failed |", content)
