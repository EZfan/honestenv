import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv import CommandResult, TaskPackage, harbor_cli
from honestenv.gates.run import check_agent


class RewardTest(unittest.TestCase):
    def test_only_valid_numeric_rewards_are_read(self):
        with tempfile.TemporaryDirectory() as directory:
            jobs_dir = Path(directory)
            result_path = jobs_dir / "job" / "trial" / "result.json"
            result_path.parent.mkdir(parents=True)
            self.assertIsNone(harbor_cli.read_reward(jobs_dir))

            for reward, valid, expected in (
                (1.0, True, 1.0), (0, True, 0), (0.5, True, 0.5),
                (None, True, None), (0, False, None), (0, None, None),
                ("0", True, None), (False, True, None), (True, True, None),
                (float("nan"), True, None), (float("inf"), True, None),
            ):
                with self.subTest(reward=reward, valid=valid):
                    result_path.write_text(json.dumps({
                        "reward_valid": valid,
                        "verifier_result": {"rewards": {"reward": reward}},
                    }))
                    actual = harbor_cli.read_reward(jobs_dir)
                    if expected is None:
                        self.assertIsNone(actual)
                    else:
                        self.assertEqual(actual, expected)

            for raw in ("{}", "[]", "not-json", '{"reward_valid":true,"verifier_result":{"rewards":{}}}'):
                with self.subTest(raw=raw):
                    result_path.write_text(raw)
                    self.assertIsNone(harbor_cli.read_reward(jobs_dir))

    @patch("honestenv.gates.run.harbor_cli.run")
    def test_gate_requires_successful_command_and_exact_reward(self, run):
        package = TaskPackage(root=Path("task"), content_hash="hash")
        for agent, expected_reward in (("oracle", 1.0), ("nop", 0.0)):
            for returncode, reward, passed in (
                (0, expected_reward, True), (0, 1 - expected_reward, False),
                (0, None, False), (0, 0.5, False), (1, expected_reward, False),
            ):
                with self.subTest(agent=agent, returncode=returncode, reward=reward):
                    run.return_value = CommandResult([], returncode, "", "", reward)
                    report = check_agent(package, agent=agent, expected_reward=expected_reward)
                    self.assertEqual(report.name, agent)
                    self.assertEqual(report.passed, passed)
                    self.assertTrue(report.details)
