#!/bin/sh
set -eu
mkdir -p /logs/verifier
chmod 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python -I - <<'PYCODE'
import sys
sys.path.insert(0, "/tests")
from runner import call
sys.path.insert(0, "/app")
add_days = call('dateshift', 'add_days')

assert add_days("2023-01-31", 1) == "2023-02-01"
assert add_days("2023-12-31", 1) == "2024-01-01"
assert add_days("2024-02-28", 1) == "2024-02-29"
assert add_days("2023-02-28", 1) == "2023-03-01"
assert add_days("2024-03-01", -1) == "2024-02-29"
assert add_days("2024-01-01", -1) == "2023-12-31"
assert add_days("2024-01-02", 0) == "2024-01-02"
assert add_days("1900-02-28", 1) == "1900-03-01"
assert add_days("2000-02-28", 1) == "2000-02-29"
PYCODE
then
    echo 1 > /logs/verifier/reward.txt
fi
