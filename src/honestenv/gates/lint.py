from .. import harbor_cli
from ..types import GateReport, TaskPackage


def check_lint(package: TaskPackage, profile: str = "factory") -> GateReport:
    if profile == "audit":
        default = harbor_cli.lint(package.root, extend_select_all=False)
        extended = harbor_cli.lint(package.root, extend_select_all=True)
        return GateReport(
            "lint",
            _audit_lint_passed(default) and _audit_lint_passed(extended),
            f"Harbor default (exit {default.returncode}):\n{default.stdout}{default.stderr}"
            f"\nHarbor --extend-select ALL (exit {extended.returncode}):\n{extended.stdout}{extended.stderr}",
        )
    result = harbor_cli.lint(package.root)
    return GateReport(
        name="lint",
        passed=result.returncode == 0,
        details=result.stderr or result.stdout,
    )


def _audit_lint_passed(result):
    if result.returncode == 0:
        return True
    if result.returncode != 1 or result.stderr.strip():
        return False
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return bool(lines) and all(
        "[root-agent]" in line
        or ("[invalid-task-config]" in line
            and "docker-compose.yaml" in line
            and "Docker Compose could not load this configuration; run docker compose config to inspect the error locally." in line)
        for line in lines
    )
