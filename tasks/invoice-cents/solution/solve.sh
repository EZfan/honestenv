#!/bin/sh
set -eu
cat > /app/money.py <<'PY'
def parse_cents(text):
    dollars, cents = text.split(".")
    return int(dollars) * 100 + int(cents)
PY
cat > /app/invoice.py <<'PY'
def line_total(unit_cents, quantity):
    return unit_cents * quantity


def invoice_total(lines):
    return sum(line_total(unit_cents, quantity) for unit_cents, quantity in lines)
PY
