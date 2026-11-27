#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python - <<'PYCODE'
import copy
import sys
sys.path.insert(0, "/app")
from jobs import order_jobs

jobs = [
    {"id": "third", "needs": ["second"]},
    {"id": "join", "needs": ["first", "independent"]},
    {"id": "second", "needs": ["first"]},
    {"id": "first", "needs": []},
    {"id": "independent", "needs": []},
]
original = copy.deepcopy(jobs)
assert order_jobs(jobs) == ["first", "independent", "second", "join", "third"]
assert jobs == original
assert order_jobs([]) == []
assert order_jobs([{"id": "a", "needs": []}, {"id": "b", "needs": []}]) == ["a", "b"]
for invalid in (
    [{"id": "a", "needs": ["missing"]}],
    [{"id": "a", "needs": ["b"]}, {"id": "b", "needs": ["a"]}],
):
    try:
        order_jobs(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid graph must raise ValueError")
PYCODE
then
    echo 1 > /logs/verifier/reward.txt
fi
