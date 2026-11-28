#!/usr/bin/env python3
"""Compare two version-compare verifier scripts on a fixed Harbor case set."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from accept_behavior_cases import TASK, VARIANTS
from honestenv.evidence import run_case

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "scripts/fixtures/version-compare/verifier-before.sh"
AFTER = TASK / "tests/test.sh"
CASES = {
    "reference": ("must_pass", None),
    "valid-padded-tuples": ("must_pass", VARIANTS["valid-padded-tuples"][2]),
    "valid-trim-zeros": ("must_pass", VARIANTS["valid-trim-zeros"][2]),
    "wrong-third-component": ("must_fail", '''def cmp_version(left, right):
    a = [int(x) for x in left.split('.')]
    b = [int(x) for x in right.split('.')]
    n = max(len(a), len(b))
    a += [0] * (n - len(a))
    b += [0] * (n - len(b))
    if n == 3 and a[:2] == b[:2] and 0 < a[2] < 10 and 0 < b[2] < 10:
        return 0
    return (a > b) - (a < b)
'''),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new directory for comparison and replay packs")
    parser.add_argument("--before", type=Path, default=BEFORE)
    parser.add_argument("--after", type=Path, default=AFTER)
    args = parser.parse_args()
    scripts = {name: path.read_bytes() for name, path in (("before", args.before), ("after", args.after))}
    args.out.mkdir(parents=True, exist_ok=False)
    output = args.out.resolve()
    rows = []
    failures = []
    for name, (expected, source) in CASES.items():
        row = {"case_id": name, "expected": expected}
        for version, script in scripts.items():
            pack = output / version / name
            try:
                with tempfile.TemporaryDirectory(prefix="honestenv-w09-") as tmp:
                    task = Path(tmp) / "version-compare"
                    shutil.copytree(TASK, task)
                    (task / "tests/test.sh").write_bytes(script)
                    if source is not None:
                        (task / "solution/solve.sh").write_text(
                            "#!/bin/sh\nset -eu\ncat > /app/version.py <<'PYCASE'\n" + source + "PYCASE\n")
                    run_case(task, pack, agent="oracle", expected=expected, confirmed_defect=True)
                run = json.loads((pack / "report.json").read_text())["runs"][0]
                row[version] = {"run_status": run["run_status"], "conclusion": run["conclusion"],
                                "reward_raw": run["reward_raw"], "evidence": f"{version}/{name}"}
            except Exception as exc:
                row[version] = {"run_status": "runner_error", "conclusion": None, "error": str(exc)}
            print(f"{name} {version}: {row[version]['run_status']} / {row[version]['conclusion']}", flush=True)
        before, after = row["before"], row["after"]
        row["changed"] = (before["run_status"], before["conclusion"]) != (after["run_status"], after["conclusion"])
        expected_conclusion = "pass" if expected == "must_pass" else "fail"
        if (before["run_status"] != "graded" or after["run_status"] != "graded"
                or after["conclusion"] != expected_conclusion
                or (expected == "must_pass" and before["conclusion"] != "pass")):
            failures.append(name)
        rows.append(row)
    result = {"schema_version": "1.0", "verifiers": {
        name: {"sha256": hashlib.sha256(script).hexdigest()} for name, script in scripts.items()},
        "cases": rows, "passed": not failures, "failures": failures}
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
