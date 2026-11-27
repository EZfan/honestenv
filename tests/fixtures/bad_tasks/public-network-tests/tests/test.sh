#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if [ "$(python /app/program.py)" = "hello" ]; then
    echo 1 > /logs/verifier/reward.txt
fi
curl https://example.com/data
