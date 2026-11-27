import argparse
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .gates.baseline import check_baseline
from .gates.lint import check_lint
from .gates.run import check_agent
from .gates.schema import check_schema
from .package import load
from .scaffold import init_task
from .types import CheckReport


def check_task(task_dir: Path, *, static_only: bool = False) -> CheckReport:
    package = load(task_dir)
    gates = [check_schema(package), check_lint(package), check_baseline(package)]
    if not static_only:
        gates.extend([
            check_agent(package, agent="oracle", expected_reward=1.0),
            check_agent(package, agent="nop", expected_reward=0.0),
        ])
    report = CheckReport(package, gates, all(gate.passed for gate in gates))
    print(f"{package.root}: {'passed' if report.passed else 'failed'}")
    for gate in gates:
        print(f"  {gate.name}: {'passed' if gate.passed else 'failed'} - {gate.details}")
    return report


def run() -> int:
    parser = argparse.ArgumentParser(prog="honestenv")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Create a task scaffold in tasks/<task>",
        description="Create tasks/<task> in the current directory. An existing empty directory is allowed; a non-empty directory requires --force.",
    )
    init_parser.add_argument("name", metavar="org/task", help="Harbor name org/task; each part starts with an ASCII letter or digit and contains only letters, digits, dots, hyphens, or underscores, without ..")
    init_parser.add_argument("--force", action="store_true", help="Overwrite scaffold files in an existing task directory")

    check_parser = subparsers.add_parser("check", help="Check a task directory")
    check_parser.add_argument("task_dir", type=Path)
    check_parser.add_argument("--out", type=Path)
    check_parser.add_argument("--static-only", action="store_true", help="Run schema, lint and factory checks only")

    test_parser = subparsers.add_parser("test-gates", help="Check tasks in tasks/")
    test_parser.add_argument("--static-only", action="store_true")

    pack_parser = subparsers.add_parser("pack", help="Copy a passing task into a dataset")
    pack_parser.add_argument("task_dir", type=Path)
    pack_parser.add_argument("--into", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "init":
            print(init_task(args.name, force=args.force))
            return 0

        if args.command == "test-gates":
            tasks_dir = Path("tasks")
            reports = [
                check_task(task_dir, static_only=args.static_only)
                for task_dir in sorted(tasks_dir.iterdir())
                if task_dir.is_dir() and (task_dir / "task.toml").is_file()
            ]
            return 0 if all(report.passed for report in reports) else 1

        report = check_task(args.task_dir, static_only=args.command == "check" and args.static_only)
        if args.command == "check":
            if args.out is not None:
                args.out.write_text(json.dumps(asdict(report), default=str, indent=2) + "\n", encoding="utf-8")
        elif report.passed:
            args.into.mkdir(parents=True, exist_ok=True)
            destination = args.into / report.package.root.name
            shutil.copytree(report.package.root, destination)
            print(destination)
        return 0 if report.passed else 1
    except (OSError, ValueError) as error:
        print(f"honestenv: {error}", file=sys.stderr)
        return 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
