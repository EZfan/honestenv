import tempfile
import unittest
from pathlib import Path

from honestenv.gates.python_verifier import python_verifier_warnings


class PythonVerifierTest(unittest.TestCase):
    def warnings(self, source):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'verify.py').write_text(source)
            return python_verifier_warnings(root)

    def test_intersection_thresholds(self):
        for source in ('assert len(actual & expected) > 2',
                       'score = len(actual.intersection(expected))\nassert score >= 2'):
            with self.subTest(source=source):
                result = self.warnings(source)
                self.assertTrue(any('HE-005: tests/verify.py:' in item for item in result))
                self.assertIn('complete sets', result[0])

    def test_exact_and_unrelated_comparisons(self):
        for source in ('assert set(actual) == set(expected)',
                       'assert len(actual & expected) > 2 and set(actual) == set(expected)',
                       'assert score > 2', 'assert len(actual) > 2'):
            with self.subTest(source=source):
                self.assertFalse(any('HE-005' in item for item in self.warnings(source)))

    def test_stdout_and_file_checks(self):
        for source in ('assert result.stdout == "ok"', 'assert output.exists()'):
            with self.subTest(source=source):
                result = self.warnings(source)
                self.assertTrue(any('HE-006: tests/verify.py:1:' in item for item in result))
        for source in ('assert result.stdout == "ok"\nassert mock.called',
                       'assert output.exists()\ndata = json.loads(output.read_text())',
                       'assert output.exists()\nkey.verify(signature, data)',
                       'assert result.returncode == 0'):
            with self.subTest(source=source):
                self.assertFalse(any('HE-006' in item for item in self.warnings(source)))

    def test_ignores_comments_and_bad_python(self):
        self.assertFalse(self.warnings('# assert output.exists()\n'))
        self.assertFalse(self.warnings('assert ('))


if __name__ == '__main__':
    unittest.main()
