#!/usr/bin/env python3
"""Run a fixed set of version-comparison cases through Harbor Docker."""
import argparse
import json
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from honestenv.case_schema import Case, Report, Run, BinaryProfile
from honestenv.evidence import run_case

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "version-compare"

VARIANTS = {
    "valid-padded-tuples": ("must_pass", "Numeric components padded with zeros compare lexicographically.", '''def cmp_version(left, right):
    a = [int(x) for x in left.split('.')]
    b = [int(x) for x in right.split('.')]
    n = max(len(a), len(b))
    a += [0] * (n - len(a))
    b += [0] * (n - len(b))
    return (a > b) - (a < b)
'''),
    "valid-trim-zeros": ("must_pass", "Removing trailing zero components preserves numeric ordering.", '''def cmp_version(left, right):
    def parse(s):
        parts = [int(x) for x in s.split('.')]
        while parts and parts[-1] == 0:
            parts.pop()
        return parts
    a, b = parse(left), parse(right)
    return (a > b) - (a < b)
'''),
    "wrong-lexical": ("must_fail", "String ordering disagrees with numeric components such as 1.10 and 1.9.", '''def cmp_version(left, right):
    return (left > right) - (left < right)
'''),
    "wrong-trailing-zeros": ("must_fail", "Tuple length incorrectly distinguishes 1.2 from 1.2.0.", '''def cmp_version(left, right):
    a, b = tuple(map(int, left.split('.'))), tuple(map(int, right.split('.')))
    return (a > b) - (a < b)
'''),
    "wrong-first-component": ("must_fail", "Comparing only the first component ignores later differences.", '''def cmp_version(left, right):
    a, b = int(left.split('.')[0]), int(right.split('.')[0])
    return (a > b) - (a < b)
'''),
    "submission-early-exit": ("must_fail", "A submission exiting without a result must be rejected.", '''def cmp_version(left, right):
    raise SystemExit(0)
'''),
    "submission-exception": ("must_fail", "A submission raising an exception must be rejected.", '''def cmp_version(left, right):
    raise RuntimeError('broken implementation')
'''),
}
VERIFIERS = {
    "verifier-missing": "#!/bin/sh\nexit 0\n",
    "verifier-nonfinite": "#!/bin/sh\nmkdir -p /logs/verifier\necho NaN > /logs/verifier/reward.txt\n",
    "verifier-early-exit": "#!/bin/sh\nexit 3\n",
    "verifier-exception": "#!/bin/sh\npython -c 'raise RuntimeError(\"verifier broke\")'\n",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new directory for replayable evidence packs")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    output = args.out.resolve()
    results = []
    failures = []
    cases = [(name, expected, basis, source, None) for name, (expected, basis, source) in VARIANTS.items()]
    cases += [(name, "unknown", "Deliberately broken verifier; no grading conclusion is valid.", None, script)
              for name, script in VERIFIERS.items()]
    expected_errors = {"verifier-missing": "RewardFileNotFoundError",
                       "verifier-nonfinite": "VerifierOutputParseError",
                       "verifier-early-exit": "RewardFileNotFoundError",
                       "verifier-exception": "RewardFileNotFoundError"}
    for name, expected, basis, source, verifier in cases:
        with tempfile.TemporaryDirectory(prefix="honestenv-w08-") as tmp:
            task = Path(tmp) / "version-compare"
            shutil.copytree(TASK, task)
            if source is not None:
                (task / "solution" / "solve.sh").write_text("#!/bin/sh\nset -eu\ncat > /app/version.py <<'PYCASE'\n" + source + "PYCASE\n")
            if verifier is not None:
                (task / "tests" / "test.sh").write_text(verifier)
            pack = output / name
            try:
                run_case(task, pack, agent="oracle", expected=expected, confirmed_defect=True)
                data = json.loads((pack / "report.json").read_text())["runs"][0]
                old_case = data["case"]
                case = Case(name, "1", "version-compare", old_case["task_version"], old_case["spec_ref"],
                            old_case["spec_sha256"], tuple(old_case["artifact_refs"]), expected, basis)
                profile = BinaryProfile(**data["profile"])
                run = Run(case, profile, data["run_status"], data["conclusion"], data["reward_raw"],
                          data["reward_valid"], data["invalid_reason"], data["harbor_version"],
                          data["honestenv_version"], tuple(data["evidence_refs"]))
                (pack / "report.json").write_text(Report((run,)).to_json() + "\n")
                results.append(replace(run, case=replace(case, spec_ref=f"{name}/{case.spec_ref}",
                                                       artifact_refs=(f"{name}/task",)),
                                       evidence_refs=(f"{name}/stdout.txt", f"{name}/stderr.txt")))
                good = ((run.run_status, run.conclusion) == ("graded", "pass" if expected == "must_pass" else "fail")
                        if verifier is None else (run.run_status == "execution_error" and run.conclusion is None
                                                  and expected_errors[name] in (pack / "stdout.txt").read_text()))
                print(f"{name}: {run.run_status} / {run.conclusion} / {run.invalid_reason}", flush=True)
                if not good:
                    failures.append(name)
            except Exception as exc:
                failures.append(name)
                print(f"{name}: runner error: {exc}", flush=True)
    (output / "batch.json").write_text(Report(tuple(results)).to_json() + "\n")
    if failures:
        print("Acceptance failed: " + ", ".join(failures), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
