import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv import CommandResult, GateReport, TaskPackage, harbor_cli
from honestenv.gates.lint import check_lint


class HarborLintTest(unittest.TestCase):
    @patch("honestenv.harbor_cli.subprocess.run")
    def test_lint_with_and_without_extended_selection(self, run):
        task_dir = Path("task directory")
        for options, argv, returncode in (
            ({}, ["harbor", "lint", "--extend-select", "ALL", str(task_dir)], 0),
            ({"extend_select_all": False}, ["harbor", "lint", str(task_dir)], 1),
        ):
            with self.subTest(options=options):
                run.return_value = subprocess.CompletedProcess(
                    argv, returncode, stdout="output", stderr="diagnostics"
                )
                self.assertEqual(
                    harbor_cli.lint(task_dir, **options),
                    CommandResult(argv, returncode, "output", "diagnostics"),
                )
                run.assert_called_with(argv, capture_output=True, text=True, check=False)

    @patch("honestenv.gates.lint.harbor_cli.lint")
    def test_gate_maps_returncode_and_details(self, lint):
        package = TaskPackage(root=Path("task directory"), content_hash="hash")
        for returncode, stdout, stderr, passed, details in (
            (0, "clean", "", True, "clean"),
            (1, "output", "diagnostics", False, "diagnostics"),
            (2, "findings", "", False, "findings"),
        ):
            with self.subTest(returncode=returncode):
                lint.return_value = CommandResult([], returncode, stdout, stderr)
                self.assertEqual(check_lint(package), GateReport("lint", passed, details))
                lint.assert_called_with(package.root)

    @patch("honestenv.gates.lint.harbor_cli.lint")
    def test_audit_reports_both_runs_and_only_known_policy_findings_pass(self, lint):
        package = TaskPackage(Path("task"), "hash")
        compose = "task/environment/docker-compose.yaml [invalid-task-config] Docker Compose could not load this configuration; run docker compose config to inspect the error locally."
        root = "task/task.toml [root-agent] agent.user: Agent user is omitted or root; configure a non-root user."
        lint.side_effect = [CommandResult([], 1, compose, ""), CommandResult([], 1, compose + "\n" + root, "")]
        report = check_lint(package, profile="audit")
        self.assertTrue(report.passed, report.details)
        self.assertIn("Harbor default", report.details)
        self.assertIn("Harbor --extend-select ALL", report.details)
        self.assertIn(compose, report.details)
        self.assertIn(root, report.details)

        for failure in (CommandResult([], 1, root + "\n[unknown-rule] issue", ""),
                        CommandResult([], 1, root, "unexpected error"),
                        CommandResult([], 2, root, ""), CommandResult([], 1, "", "")):
            with self.subTest(failure=failure):
                lint.side_effect = [CommandResult([], 0, "", ""), failure]
                self.assertFalse(check_lint(package, profile="audit").passed)
