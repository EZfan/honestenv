#!/bin/sh
set -eu
cat > /app/records.py <<'PY'
def sort_records(records):
    return sorted(records, key=lambda record: (-int(record["qty"]), record["name"]))
PY
