#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python - <<'PY'
import sys
sys.path.insert(0, "/app")
from money import parse_cents
from invoice import line_total, invoice_total

for text, expected in [("0.00", 0), ("0.10", 10), ("1.13", 113), ("12.34", 1234)]:
    assert parse_cents(text) == expected
assert line_total(113, 0) == 0
assert line_total(113, 3) == 339
assert invoice_total([]) == 0
assert invoice_total([(113, 3), (10, 2), (1234, 0)]) == 359
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
