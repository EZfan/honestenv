#!/bin/sh
set -eu
mkdir -p /logs/verifier
chmod 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt
if python -I - <<'PY'
import os
import sys
sys.path.insert(0, "/tests")
from runner import run_binary
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as directory:
    os.chmod(directory, 0o755)
    path = Path(directory) / 'input'
    path.write_text('one|two|three\nshort\n|last\n')
    def run(*args):
        return run_binary(['/app/cutfield', *args])
    result = run('-d', '|', '-f', '2', str(path))
    assert result.returncode == 0 and result.stdout == 'two\n\nlast\n'
    result = run('-d', '|', '-f', '1', str(path))
    assert result.returncode == 0 and result.stdout == 'one\nshort\n\n'
    assert run('-d', '|', '-f', '1', str(path) + '.missing').returncode == 1
    for args in [('-f', '1', str(path)), ('-d', '|', str(path)),
                 ('-d', '|', '-f', '0', str(path)), ('-d', '|', '-f', 'x', str(path))]:
        assert run(*args).returncode == 1
PY
then
    echo 1 > /logs/verifier/reward.txt
fi
