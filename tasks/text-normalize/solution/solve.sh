#!/bin/sh
set -eu
cat > /app/textnorm/spaces.py <<'PY'
def collapse_spaces(text):
    return " ".join(text.split())
PY
cat > /app/textnorm/case.py <<'PY'
def fold_case(text):
    return text.casefold()
PY
cat > /app/textnorm/__init__.py <<'PY'
from .spaces import collapse_spaces
from .case import fold_case


def normalize(text):
    return fold_case(collapse_spaces(text))
PY
