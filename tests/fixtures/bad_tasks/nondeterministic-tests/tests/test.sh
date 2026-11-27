#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if [ "$(od -An -N1 -tu1 /dev/urandom)" -eq 0 ]; then
    exit 1
fi
if [ "$(python /app/program.py)" = "hello" ]; then
    echo 1 > /logs/verifier/reward.txt
fi
