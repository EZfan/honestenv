import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv import cli
from honestenv.types import GateReport


class CLITest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.task = self.root / "task"
        self.task.mkdir()
        files = {
            "instruction.md": "Complete the task.\n",
            "task.toml": 'schema_version = "1.4"\n[environment]\ndocker_image = "alpine"\n',
            "tests/test.sh": "#!/bin/sh\n",
            "solution/solve.sh": "#!/bin/sh\n",
        }
        for name, content in files.items():
            path = self.task / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        lint = patch("honestenv.cli.check_lint", return_value=GateReport("lint", True, "clean"))
        self.mock_lint = lint.start()
        self.addCleanup(lint.stop)
        agent = patch(
            "honestenv.cli.check_agent",
            side_effect=lambda package, *, agent, expected_reward: GateReport(agent, True, f"Reward {expected_reward}"),
        )
        self.mock_agent = agent.start()
        self.addCleanup(agent.stop)

    def run_cli(self, *args):
        with patch("sys.argv", ["honestenv", *map(str, args)]):
            with self.assertRaises(SystemExit) as result:
                cli.main()
            return result.exception.code

    def test_check_writes_report_and_returns_gate_status(self):
        output = self.root / "report.json"
        self.assertEqual(self.run_cli("check", self.task, "--out", output), 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(report["package"]["root"], str(self.task))
        self.assertEqual([gate["name"] for gate in report["gates"]], ["schema", "lint", "oracle", "nop"])
        self.mock_lint.return_value = GateReport("lint", False, "issues")
        self.assertEqual(self.run_cli("check", self.task, "--out", output), 1)
        self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["passed"])

    def test_test_gates_checks_each_task_with_static_only(self):
        tasks = self.root / "tasks"
        tasks.mkdir()
        self.task.rename(tasks / "valid")
        invalid = tasks / "invalid"
        invalid.mkdir()
        (invalid / "task.toml").write_text("", encoding="utf-8")
        (tasks / "ignored").mkdir()
        old_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, old_cwd)
        self.assertEqual(self.run_cli("test-gates", "--static-only"), 1)
        self.assertEqual(self.mock_lint.call_count, 2)
        self.mock_agent.assert_not_called()
        (invalid / "task.toml").unlink()
        self.assertEqual(self.run_cli("test-gates"), 0)
        self.assertEqual(self.mock_agent.call_count, 2)

    def test_pack_copies_only_passing_task(self):
        destination = self.root / "dataset"
        self.mock_lint.return_value = GateReport("lint", False, "issues")
        self.assertEqual(self.run_cli("pack", self.task, "--into", destination), 1)
        self.assertFalse(destination.exists())
        self.mock_lint.return_value = GateReport("lint", True, "clean")
        self.assertEqual(self.run_cli("pack", self.task, "--into", destination), 0)
        self.assertEqual((destination / "task" / "instruction.md").read_text(), "Complete the task.\n")


if __name__ == "__main__":
    unittest.main()
