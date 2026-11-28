import json
import unittest

from honestenv.case_schema import BinaryProfile, Case, Report, Run, record_reward


class CaseSchemaTest(unittest.TestCase):
    def setUp(self):
        self.case = Case("case", "1", "task", "1", "spec", "digest", ("artifact",),
                         "must_fail", "requirement")
        self.profile = BinaryProfile("config-1", 1, 0)

    def record(self, value, valid=True):
        return record_reward(self.case, self.profile,
                             {"reward_valid": valid, "verifier_result": {"rewards": {"reward": value}}},
                             harbor_version="0.27.0", honestenv_version="0.1.1")

    def test_binary_outcomes_and_report(self):
        passed, failed = self.record(1), self.record(0)
        self.assertEqual((passed.run_status, passed.conclusion), ("graded", "pass"))
        self.assertEqual((failed.run_status, failed.conclusion), ("graded", "fail"))
        data = json.loads(Report((passed, failed)).to_json())
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["runs"][1]["profile"]["check_config_version"], "config-1")
        self.assertEqual(data["runs"][1]["case"]["expected"], "must_fail")

    def test_invalid_values_are_preserved_and_not_graded(self):
        for value, valid, reason, raw in ((float("nan"), True, "non_finite_reward", "NaN"),
                                          (float("inf"), True, "non_finite_reward", "Infinity"),
                                          ("bad", True, "invalid_reward_type", '"bad"'),
                                          (0.5, True, "unmapped_reward", "0.5"),
                                          (0, False, "harbor_reward_invalid", "0")):
            with self.subTest(value=value):
                run = self.record(value, valid)
                self.assertEqual((run.run_status, run.conclusion, run.reward_valid), ("execution_error", None, False))
                self.assertEqual((run.invalid_reason, run.reward_raw), (reason, raw))
                json.loads(Report((run,)).to_json(), parse_constant=lambda x: self.fail(x))
        missing = record_reward(self.case, self.profile, {}, harbor_version="0.27.0", honestenv_version="0.1.1")
        self.assertEqual((missing.invalid_reason, missing.reward_raw), ("missing_reward", None))

    def test_invariants(self):
        for values in (("v", 1, 1), ("v", float("nan"), 0), ("", 1, 0)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                BinaryProfile(*values)
        with self.assertRaises(ValueError):
            Run(self.case, self.profile, "execution_error", "fail", "0", False, "error", "0.27.0", "0.1.1")
        with self.assertRaises(ValueError):
            Run(self.case, self.profile, "graded", "pass", "0", True, None, "0.27.0", "0.1.1")
        for status in ("unsupported", "skipped"):
            run = Run(self.case, self.profile, status, None, None, False, "not_run", "0.27.0", "0.1.1")
            self.assertEqual(json.loads(Report((run,)).to_json())["runs"][0]["run_status"], status)
