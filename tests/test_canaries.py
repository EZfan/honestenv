import unittest
from pathlib import Path

from honestenv.cli import check_task


ROOT = Path(__file__).resolve().parent.parent
BAD_TASKS = ROOT / "tests" / "fixtures" / "bad_tasks"
REASONS = {
    "always-reward-one": "reward: reward 1 is not conditional on a check of a packaged artifact",
    "public-network-tests": "test-network:",
    "missing-timeout": "headroom:",
    "reward-one-nonzero-exit": "reward: reward 1 can be followed by a non-zero exit",
    "nondeterministic-tests": "reward: nondeterministic test material",
    "unpinned-image": "image:",
    "shared-verifier-mode": "verifier:",
    "unrestricted-network": "network:",
    "root-agent": "agent:",
    "never-reward-one": "reward: no reward 1 write found",
}


class CanaryTest(unittest.TestCase):
    def test_bad_tasks_are_rejected_for_the_expected_reason(self):
        self.assertEqual({path.name for path in BAD_TASKS.iterdir() if path.is_dir()}, set(REASONS))
        for name, reason in REASONS.items():
            with self.subTest(task=name):
                report = check_task(BAD_TASKS / name, static_only=True)
                self.assertFalse(report.passed)
                factory = next(gate for gate in report.gates if gate.name == "factory")
                self.assertFalse(factory.passed)
                self.assertIn(reason, factory.details)

    def test_shipped_tasks_pass_static_checks(self):
        for name in ("reservation-window", "version-compare"):
            with self.subTest(task=name):
                report = check_task(ROOT / "tasks" / name, static_only=True)
                factory = next(gate for gate in report.gates if gate.name == "factory")
                self.assertTrue(factory.passed, factory.details)
                self.assertTrue(report.passed, report.gates)


if __name__ == "__main__":
    unittest.main()
