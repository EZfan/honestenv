import subprocess

from .. import harbor_cli
from ..types import GateReport, TaskPackage


def check_lint(package: TaskPackage) -> GateReport:
    result = harbor_cli.lint(package.root)
    return GateReport(
        name="lint",
        passed=result.returncode == 0,
        details=result.stderr or result.stdout,
    )


def check_audit_lint(package: TaskPackage) -> GateReport:
    default = harbor_cli.lint(package.root, extend_select_all=False)
    extended = harbor_cli.lint(package.root, extend_select_all=True)
    compose_ok = False
    if "Docker Compose could not load this configuration" in default.stdout + extended.stdout:
        compose_ok = _compose_host_incompatibility(package.root)
    return GateReport(
        "lint",
        _audit_lint_passed(default, compose_ok) and _audit_lint_passed(extended, compose_ok),
        f"Harbor default (exit {default.returncode}):\n{default.stdout}{default.stderr}"
        f"\nHarbor --extend-select ALL (exit {extended.returncode}):\n{extended.stdout}{extended.stderr}"
        f"\nCompose host incompatibility confirmed: {compose_ok}",
    )


def _compose_host_incompatibility(root):
    path = (root / "environment/docker-compose.yaml").absolute()
    command = ["docker", "compose", "--profile", "*", "-f", str(path), "config", "--format", "json"]
    try:
        harbor_probe = subprocess.run(command + ["--no-env-resolution", "--no-path-resolution", "--no-consistency"],
                                      capture_output=True, text=True, timeout=30)
        if harbor_probe.returncode == 0 or "unknown flag: --no-env-resolution" not in harbor_probe.stderr:
            return False
        compatible_probe = subprocess.run(command + ["--no-interpolate", "--no-path-resolution", "--no-consistency"],
                                          capture_output=True, text=True, timeout=30)
        return compatible_probe.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _audit_lint_passed(result, compose_ok):
    if result.returncode == 0:
        return True
    if result.returncode != 1 or result.stderr.strip():
        return False
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return bool(lines) and all(
        "[root-agent]" in line
        or (compose_ok and "[invalid-task-config]" in line
            and "docker-compose.yaml" in line
            and "Docker Compose could not load this configuration; run docker compose config to inspect the error locally." in line)
        for line in lines
    )
