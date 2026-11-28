import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv.evidence import run_case


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = self.root / "original" / "task"
        self.task.mkdir(parents=True)
        (self.task / "task.toml").write_text('version = "1"\n')
        self.bin = self.root / "bin"
        self.bin.mkdir()
        harbor = self.bin / "harbor"
        harbor.write_text("""#!/bin/sh
if [ "$1" = "--version" ]; then echo 'harbor 0.27.0'; exit 0; fi
while [ "$#" -gt 0 ]; do
  case "$1" in
    -p) task="$2"; shift 2 ;;
    --jobs-dir) jobs="$2"; shift 2 ;;
    *) shift ;;
  esac
done
test -f "$task/task.toml" || exit 4
mkdir -p "$jobs/job/trial"
printf '%s' '{"reward_valid":true,"verifier_result":{"rewards":{"reward":0}}}' > "$jobs/job/trial/result.json"
echo replay-ok
""")
        harbor.chmod(0o755)
        self.env = patch.dict(os.environ, {"PATH": str(self.bin) + os.pathsep + os.environ["PATH"]})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_clean_directory_replay_after_original_deleted(self):
        pack = self.root / "pack"
        self.assertTrue(run_case(self.task, pack, agent="oracle", expected="must_pass"))
        report = json.loads((pack / "report.json").read_text())
        self.assertEqual(report["runs"][0]["reward_raw"], "0")
        self.assertEqual(report["runs"][0]["case"]["spec_ref"], "task/task.toml")
        shutil.rmtree(self.task.parent)
        clean = self.root / "clean"
        clean.mkdir()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run([sys.executable, "-m", "honestenv.cli", "replay", str(pack)], cwd=clean,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("replay-ok", result.stdout)
        (pack / "task" / "task.toml").write_text("changed")
        result = subprocess.run([sys.executable, "-m", "honestenv.cli", "replay", str(pack)], cwd=clean,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_secrets_rejected_and_success_not_retained(self):
        pack = self.root / "pack"
        self.assertFalse(run_case(self.task, pack, agent="nop", expected="must_fail"))
        self.assertFalse(pack.exists())
        (self.task / ".env").write_text("x")
        with self.assertRaises(ValueError):
            run_case(self.task, pack, agent="nop", expected="must_fail", confirmed_defect=True)
        (self.task / ".env").unlink()
        (self.task / "task.toml").write_text('api_key = "hidden-value"')
        with self.assertRaises(ValueError):
            run_case(self.task, pack, agent="nop", expected="must_fail", confirmed_defect=True)
        self.assertFalse(pack.exists())

    def test_known_environment_patterns_are_rejected(self):
        for secret in ('AWS_SECRET_ACCESS_KEY=examplevalue', '"api_key": "examplevalue"'):
            (self.task / "task.toml").write_text(secret)
            with self.subTest(secret=secret), self.assertRaises(ValueError):
                run_case(self.task, self.root / "pack", agent="nop", expected="must_fail")
