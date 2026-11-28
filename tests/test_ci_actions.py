import io
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]


class CommentPublicationTests(unittest.TestCase):
    def test_http_failures_are_reported_for_forks_and_other_prs(self):
        for fork, code in [(True, 403), (False, 403), (False, 500)]:
            with self.subTest(fork=fork, code=code), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'report').write_text('checkup')
                (root / 'event').write_text(json.dumps({'pull_request': {'head': {'repo': {'fork': fork}}}}))
                env = {'REPORT_PATH': str(root / 'report'), 'GITHUB_EVENT_PATH': str(root / 'event'),
                       'GITHUB_API_URL': 'https://example.test', 'GITHUB_REPOSITORY': 'org/repo',
                       'PR_NUMBER': '1', 'GH_TOKEN': 'token'}
                error = HTTPError('https://example.test', code, 'failure', {}, None)
                output = io.StringIO()
                with patch.dict(os.environ, env), patch('urllib.request.urlopen', side_effect=error), \
                        patch('sys.stdout', output), self.assertRaises(HTTPError):
                    runpy.run_path(str(ROOT / '.github/actions/runtime/comment.py'))
                self.assertEqual('read-only' in output.getvalue(), fork and code == 403)

    def test_workflow_records_comment_failure_without_failing_gates(self):
        action = (ROOT / '.github/actions/runtime/action.yml').read_text()
        self.assertIn('continue-on-error: true', action)
        self.assertIn("steps.comment.outcome == 'failure'", action)
        self.assertIn('GITHUB_STEP_SUMMARY', action)


if __name__ == '__main__':
    unittest.main()
