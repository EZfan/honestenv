import importlib.util
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
