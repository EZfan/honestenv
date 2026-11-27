#!/bin/sh
set -eu

cat > /app/reservation.py <<'PY'
def is_reserved(minute: int, start: int, end: int) -> bool:
    """Return whether a minute falls inside a reservation."""
    return start <= minute < end
PY
