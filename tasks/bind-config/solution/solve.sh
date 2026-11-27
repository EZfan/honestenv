#!/bin/sh
set -eu
cat > /app/config.toml <<'TOML'
host = "127.0.0.1"
port = 8000
workers = 2
TOML
