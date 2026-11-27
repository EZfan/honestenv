#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python - <<'PY'
import sys
sys.path.insert(0, "/app")
from records import sort_records

records = [
    {"name": "zebra", "qty": "10", "id": "first"},
    {"name": "nine", "qty": "9"},
    {"name": "zebra", "qty": "10", "id": "second"},
    {"name": "hundred", "qty": "100"},
    {"name": "apple", "qty": "10"},
]
original = list(records)
assert sort_records(records) == [records[3], records[4], records[0], records[2], records[1]]
assert records == original
assert sort_records([]) == []
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
