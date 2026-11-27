#!/bin/sh
set -eu

cat > /app/version.py <<'PY'
from itertools import zip_longest


def cmp_version(left: str, right: str) -> int:
    """Compare two dotted versions numerically."""
    left_parts = map(int, left.split("."))
    right_parts = map(int, right.split("."))
    for left_part, right_part in zip_longest(left_parts, right_parts, fillvalue=0):
        if left_part != right_part:
            return 1 if left_part > right_part else -1
    return 0
PY
