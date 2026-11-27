#!/bin/sh
set -eu
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python - <<'PY'
import sys
import tomllib
with open('/app/config.toml', 'rb') as config:
    settings = tomllib.load(config)
assert settings == {'host': '127.0.0.1', 'port': 8000, 'workers': 2}
sys.path.insert(0, '/app')
from app import load_settings, bind_address
host, port, workers = load_settings()
assert type(host) is str and host == '127.0.0.1'
assert type(port) is int and port == 8000
assert type(workers) is int and workers == 2
assert bind_address() == '127.0.0.1:8000'
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
