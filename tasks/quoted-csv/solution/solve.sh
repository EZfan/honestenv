#!/bin/sh
set -eu
cat > /app/csvrow.py <<'PY'
import csv


def parse_csv_row(line):
    return next(csv.reader([line]))


def parse_csv(text):
    return [parse_csv_row(line) for line in text.splitlines()]
PY
