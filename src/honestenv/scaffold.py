import re
from pathlib import Path


TRUSTED_RUNNER = (Path(__file__).parent / "trusted_runner.py").read_text(encoding="utf-8")

IMAGE = "python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b"


def init_task(name: str, *, force: bool = False) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*", name) or ".." in name:
        raise ValueError(
            "Task name must be org/task, using letters, digits, dots, hyphens and underscores; "
            "each part must start with a letter or digit and cannot contain '..'"
        )

    destination = Path("tasks") / name.split("/")[1]
    if destination.parent.is_symlink() or destination.is_symlink():
        raise OSError(f"Refusing to write through a symbolic link: {destination}")
    if destination.exists() and any(destination.iterdir()) and not force:
        raise FileExistsError(f"{destination} is not empty; use --force to overwrite scaffold files")

    files = {
        "instruction.md": """# Repair the rectangle area calculation

Fix `rectangle_area(width, height)` in `/app/area.py`. Both arguments are
non-negative integers. Return the integer area of the rectangle, including
zero when either dimension is zero. Preserve the function name and argument
order and leave the corrected source at `/app/area.py`.
""",
        "task.toml": f'''schema_version = "1.4"
artifacts = ["/app/area.py"]

[task]
name = "{name}"

[metadata]
difficulty = "easy"
category = "programming"
tags = ["python", "program-repair"]

[verifier]
environment_mode = "separate"
timeout_sec = 30.0

[agent]
timeout_sec = 120.0
user = "agent"

[environment]
network_mode = "no-network"
cpus = 1
memory_mb = 512
storage_mb = 1024
''',
        "environment/Dockerfile": f"""FROM {IMAGE}

RUN useradd --create-home agent
WORKDIR /app
COPY --chown=agent:agent area.py /app/area.py
RUN chown agent:agent /app
""",
        "environment/area.py": """def rectangle_area(width: int, height: int) -> int:
    return width + height
""",
        "tests/Dockerfile": f"""FROM {IMAGE}

WORKDIR /app
COPY test.sh /tests/test.sh
COPY runner.py /tests/runner.py
""",
        "tests/runner.py": TRUSTED_RUNNER,
        "tests/test.sh": """#!/bin/sh
set -eu

mkdir -p /logs/verifier
chmod 700 /logs/verifier
echo 0 > /logs/verifier/reward.txt

if python -I - <<'PYTHON'
import sys

sys.path.insert(0, "/tests")
from runner import call
rectangle_area = call("area", "rectangle_area")

for width, height in [(0, 5), (7, 0), (1, 1), (2, 3), (10, 8)]:
    actual = rectangle_area(width, height)
    assert type(actual) is int and actual == width * height
PYTHON
then
    echo 1.0 > /logs/verifier/reward.txt
fi
""",
        "solution/solve.sh": """#!/bin/sh
set -eu

cat > /app/area.py <<'PYTHON'
def rectangle_area(width: int, height: int) -> int:
    return width * height
PYTHON
""",
    }

    for relative_path in files:
        path = destination / relative_path
        if path.parent.is_symlink() or path.is_symlink():
            raise OSError(f"Refusing to write through a symbolic link: {path}")

    for relative_path, content in files.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if path.suffix == ".sh":
            path.chmod(0o755)
    return destination
