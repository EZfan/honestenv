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
normalize = call('textnorm', 'normalize')
collapse_spaces = call('textnorm.spaces', 'collapse_spaces')
fold_case = call('textnorm.case', 'fold_case')

assert collapse_spaces(" \tOne   Two\n\u2003Three ") == "One Two Three"
assert fold_case("Straße MIXED") == "strasse mixed"
assert normalize(" \tStraße   MIXED\n ") == "strasse mixed"
assert normalize("\t\n") == ""
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
