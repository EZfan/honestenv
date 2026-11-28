import tempfile
import unittest
from pathlib import Path

from honestenv.gates.baseline import check_baseline
from honestenv.types import TaskPackage


class BaselineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "tests").mkdir()
        (self.root / "environment").mkdir()
        self.config = '''schema_version = "1.4"
artifacts = ["/app/program.py"]
[environment]
network_mode = "no-network"
[agent]
user = "agent"
[verifier]
environment_mode = "separate"
timeout_sec = 30.0
'''
        self.script = '#!/bin/sh\nset -eu\necho 0 > /logs/verifier/reward.txt\nif python /app/program.py; then\n echo 1 > /logs/verifier/reward.txt\nfi\n'
        self.dockerfile = 'FROM python:3.12@sha256:' + 'a' * 64 + '\n'

    def check(self):
        (self.root / 'task.toml').write_text(self.config)
        (self.root / 'tests/test.sh').write_text(self.script)
        (self.root / 'environment/Dockerfile').write_text(self.dockerfile)
        return check_baseline(TaskPackage(self.root, ''))

    def test_valid(self):
        self.assertTrue(self.check().passed)

    def test_policy_failures(self):
        cases = [
            ('image:', 'dockerfile', 'FROM python:3.12\n'),
            ('verifier:', 'config', self.config.replace('environment_mode = "separate"', '')),
            ('network:', 'config', self.config.replace('no-network', 'public')),
            ('headroom:', 'config', self.config.replace('30.0', '14.0')),
            ('agent:', 'config', self.config.replace('user = "agent"', 'user = "root"')),
            ('test-network:', 'script', self.script + '\ncurl https://example.com/file\n'),
            ('reward: reward 1 is not conditional', 'script', 'python /app/program.py\necho 1 > /logs/verifier/reward.txt\n'),
            ('reward: reward 1 can be followed', 'script', self.script + 'exit 1\n'),
            ('reward: nondeterministic', 'script', self.script + 'echo $RANDOM\n'),
            ('reward: no reward 1', 'script', self.script.replace('echo 1', 'echo 0')),
            ('reward: test does not reference', 'script', self.script.replace('/app/program.py', '/app/other.py')),
        ]
        for reason, field, value in cases:
            with self.subTest(reason=reason):
                old = getattr(self, field)
                setattr(self, field, value)
                result = self.check()
                self.assertFalse(result.passed)
                self.assertIn(reason, result.details)
                setattr(self, field, old)

    def test_allowlist_and_headroom(self):
        self.config = self.config.replace('network_mode = "no-network"', 'network_mode = "allowlist"\nallowed_hosts = ["example.com"]')
        self.config += '\n[metadata]\nexpected_oracle_runtime_sec = 10.0\n'
        self.assertTrue(self.check().passed)
        self.config = self.config.replace('example.com', '*').replace('10.0', '11.0')
        result = self.check()
        self.assertIn('network:', result.details)
        self.assertIn('headroom:', result.details)


if __name__ == '__main__':
    unittest.main()

class AuditBaselineTest(BaselineTest):
    def audit(self):
        (self.root / 'task.toml').write_text(self.config)
        (self.root / 'tests/test.sh').write_text(self.script)
        (self.root / 'environment/Dockerfile').write_text(self.dockerfile)
        return check_baseline(TaskPackage(self.root, ''), profile='audit')

    def test_factory_findings_are_informational(self):
        self.dockerfile = 'FROM python:3.12\nRUN curl https://example.com/file\n'
        report = self.audit()
        self.assertTrue(report.passed, report.details)
        self.assertIn('image:', report.details)
        self.assertIn('build-network:', report.details)
        self.assertNotIn('test-network: environment/Dockerfile', report.details)
        self.assertFalse(self.check().passed)

    def test_status_and_helper_reward(self):
        self.script = '''write_reward() { printf '%s\\n' "$1" > /logs/verifier/reward.txt; }
python3 -m pytest /tests/test_outputs.py
status=$?
if [ "$status" -eq 0 ]; then write_reward 1; else write_reward 0; fi
'''
        self.assertTrue(self.audit().passed, self.audit().details)

    def test_integrity_failures(self):
        for script in (
            'echo 1 > /logs/verifier/reward.txt\n',
            'false; status=$?; if [ "$status" -eq 1 ]; then echo 1 > /logs/verifier/reward.txt; fi\n',
            'if test 1 = 1; then echo 1 > /logs/verifier/reward.txt; fi\n',
            'python3 -m pytest; status=$?\nif [ "$status" -ne 0 ]; then echo 1 > /logs/verifier/reward.txt; fi\n',
            self.script + 'exit 1\n',
        ):
            with self.subTest(script=script):
                self.script = script
                self.assertFalse(self.audit().passed)

    def test_delegated_rewardkit(self):
        self.script = 'python3 -I /tests/verify.py\n'
        (self.root / 'tests/verify.py').write_text('from rewardkit import run\nrun("/tests")\n')
        self.assertTrue(self.audit().passed, self.audit().details)
        (self.root / 'tests/verify.py').unlink()
        self.assertTrue(self.audit().passed)
        self.assertIn('integrity unknown', self.audit().details)
        self.script = 'python3 -I -m rewardkit /tests\n'
        self.assertTrue(self.audit().passed, self.audit().details)

    def test_runtime_network_and_delegated_python_are_observations(self):
        self.script = 'curl https://example.com/file\npython3 /tests/verify.py\n'
        (self.root / 'tests/verify.py').write_text('from pathlib import Path\nPath("reward.txt").write_text("1")\n')
        report = self.audit()
        self.assertTrue(report.passed, report.details)
        self.assertIn('test-network: tests/test.sh', report.details)
        self.assertIn('integrity not established', report.details)
        self.assertNotIn('reward: no reward 1 write found', report.details)

    def test_unrelated_echo_is_not_a_reward(self):
        self.script = 'echo 1 > /tmp/output\n'
        report = self.audit()
        self.assertTrue(report.passed, report.details)
        self.assertIn('integrity unknown', report.details)
