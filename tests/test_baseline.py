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
