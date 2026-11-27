#!/bin/sh
set -eu

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if python - <<'PY'
import sys

sys.path.insert(0, "/app")
from reservation import is_reserved

cases = [
    (59, 60, 90, False),
    (60, 60, 90, True),
    (75, 60, 90, True),
    (89, 60, 90, True),
    (90, 60, 90, False),
    (91, 60, 90, False),
    (0, 0, 1, True),
    (1, 0, 1, False),
    (1439, 1439, 1440, True),
    (1440, 1439, 1440, False),
    (0, 0, 0, False),
    (720, 720, 720, False),
    (1440, 1440, 1440, False),
]

for minute, start, end, expected in cases:
    actual = is_reserved(minute, start, end)
    assert actual is expected, (
        f"is_reserved({minute}, {start}, {end}): "
        f"expected {expected}, got {actual!r}"
    )
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
