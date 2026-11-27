#!/bin/sh
set -eu
cat > /app/dateshift.py <<'PYCODE'
from datetime import date as calendar_date, timedelta


def add_days(date, days):
    result = calendar_date.fromisoformat(date) + timedelta(days=days)
    return result.isoformat()
PYCODE
