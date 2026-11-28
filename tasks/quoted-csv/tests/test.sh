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
parse_csv_row = call('csvrow', 'parse_csv_row')
parse_csv = call('csvrow', 'parse_csv')

assert parse_csv_row("alpha,beta") == ["alpha", "beta"]
assert parse_csv_row('one,"two,three",four') == ["one", "two,three", "four"]
assert parse_csv_row('"say ""hello""",,end') == ['say "hello"', "", "end"]
assert parse_csv('a,b\r\n"c,d",e\n\n') == [["a", "b"], ["c,d", "e"], []]
assert parse_csv("") == []
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
