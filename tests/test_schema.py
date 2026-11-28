import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv.gates.schema import check_audit_schema, check_schema
from honestenv.types import TaskPackage


class SchemaTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.package = TaskPackage(root=self.root, content_hash="hash")
        files = {
            "instruction.md": "Complete the task.\n",
            "task.toml": 'schema_version = "1.4"\n[verifier]\nenvironment_mode = "separate"\n',
            "tests/test.sh": "#!/bin/sh\n",
            "environment/Dockerfile": "FROM alpine\n",
            "solution/solve.sh": "#!/bin/sh\n",
        }
        for relative_path, content in files.items():
            path = self.root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def test_valid_directory(self):
        report = check_schema(self.package)
        self.assertEqual(report.name, "schema")
        self.assertTrue(report.passed, report.details)

        (self.root / "environment/Dockerfile").unlink()
        (self.root / "task.toml").write_text(
            'schema_version = "1.4"\n[environment]\ndocker_image = "alpine"\n',
            encoding="utf-8",
        )
        report = check_schema(self.package)
        self.assertTrue(report.passed, report.details)

    def test_missing_files(self):
        for relative_path in (
            "instruction.md",
            "task.toml",
            "tests/test.sh",
            "environment/Dockerfile",
            "solution/solve.sh",
        ):
            with self.subTest(relative_path=relative_path):
                path = self.root / relative_path
                content = path.read_bytes()
                path.unlink()
                try:
                    report = check_schema(self.package)
                    self.assertEqual(report.name, "schema")
                    self.assertFalse(report.passed)
                    self.assertIn(relative_path, report.details)
                finally:
                    path.write_bytes(content)

    def test_wrong_version(self):
        for config in ('schema_version = "1.3"', "schema_version = 1.4", ""):
            with self.subTest(config=config):
                (self.root / "task.toml").write_text(config, encoding="utf-8")
                report = check_schema(self.package)
                self.assertFalse(report.passed)
                self.assertIn("schema_version", report.details)

    def test_audit_versions_and_verifier_policy(self):
        for version in ('', 'schema_version = 1', 'schema_version = 1.0',
                        'schema_version = "1.1"', 'schema_version = 1.2',
                        'schema_version = "1.3"', 'schema_version = 1.4',
                        'schema_version = "2.0"'):
            with self.subTest(version=version):
                (self.root / "task.toml").write_text(version + '\n[verifier]\nenvironment_mode = "shared"\n')
                report = check_audit_schema(self.package)
                self.assertTrue(report.passed, report.details)
                self.assertIn("schema_version:", report.details)
        for version in ('schema_version = true', 'schema_version = "3.0"', 'schema_version = 1.5'):
            with self.subTest(version=version):
                (self.root / "task.toml").write_text(version)
                self.assertFalse(check_audit_schema(self.package).passed)

    def test_audit_requires_readable_scripts(self):
        original = Path.read_bytes
        for relative_path in ("tests/test.sh", "solution/solve.sh"):
            with self.subTest(path=relative_path):
                def read_bytes(path):
                    if path == self.root / relative_path:
                        raise PermissionError("denied")
                    return original(path)
                with patch.object(Path, "read_bytes", read_bytes):
                    self.assertIn(relative_path, check_audit_schema(self.package).details)
                    self.assertTrue(check_schema(self.package).passed)
