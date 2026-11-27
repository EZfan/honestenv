#!/bin/sh
set -eu
cat > /app/cutfield <<'PY'
#!/usr/bin/env python3
import argparse
import sys

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-d', required=True)
parser.add_argument('-f', required=True)
parser.add_argument('file')
try:
    args = parser.parse_args()
    if len(args.d) != 1 or not args.f.isascii() or not args.f.isdecimal() or int(args.f) < 1:
        raise ValueError
    with open(args.file) as source:
        for line in source:
            fields = line.rstrip('\n').split(args.d)
            index = int(args.f) - 1
            print(fields[index] if index < len(fields) else '')
except (SystemExit, ValueError, OSError):
    sys.exit(1)
PY
chmod 755 /app/cutfield
