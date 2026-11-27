#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python - <<'PY'
import sys
sys.path.insert(0, "/app")
from textnorm import normalize
from textnorm.spaces import collapse_spaces
from textnorm.case import fold_case

assert collapse_spaces(" \tOne   Two\n\u2003Three ") == "One Two Three"
assert fold_case("Straße MIXED") == "strasse mixed"
assert normalize(" \tStraße   MIXED\n ") == "strasse mixed"
assert normalize("\t\n") == ""
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
