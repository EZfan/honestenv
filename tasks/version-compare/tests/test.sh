#!/bin/sh
set -eu

mkdir -p /logs/verifier
chmod 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt

if python -I - <<'PY'
import sys
sys.path.insert(0, "/tests")
from runner import call

sys.path.insert(0, "/app")
cmp_version = call('version', 'cmp_version')

cases = [
    ("1.10", "1.9", 1),
    ("1.9", "1.10", -1),
    ("2", "10", -1),
    ("1.2", "1.2", 0),
    ("1.2", "1.2.0", 0),
    ("1.0.0", "1", 0),
    ("1.0.1", "1", 1),
    ("1", "1.0.1", -1),
    ("0", "0.0.0", 0),
    ("01.002", "1.2", 0),
    ("1.2.10", "1.3", -1),
    ("1.2.10", "1.2.9", 1),
]

for left, right, expected in cases:
    actual = cmp_version(left, right)
    assert type(actual) is int and actual == expected, (
        f"cmp_version({left!r}, {right!r}): "
        f"expected {expected}, got {actual!r}"
    )
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
