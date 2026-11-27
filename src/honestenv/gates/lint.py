from .. import harbor_cli
from ..types import GateReport, TaskPackage


def check_lint(package: TaskPackage) -> GateReport:
    result = harbor_cli.lint(package.root)
    return GateReport(
        name="lint",
        passed=result.returncode == 0,
        details=result.stderr or result.stdout,
    )
