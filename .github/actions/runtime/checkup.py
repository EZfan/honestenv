"""Plan runtime gates and generate a Markdown checkup for the caller's tasks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def select_runtime(changed_paths: list[str], task_names: list[str]) -> list[str]:
    """Return the shipped task names requiring runtime checks, in sorted order."""
    names = set(task_names)
    selected = set()
    for path in changed_paths:
        parts = path.split("/")
        if (parts[0] == "src" or path == "pyproject.toml"
                or path.startswith((".github/workflows/", ".github/actions/"))):
            return sorted(names)
        if len(parts) > 1 and parts[0] == "tasks" and parts[1] in names:
            selected.add(parts[1])
    return sorted(selected)


def diff_command(base_sha: str) -> list[str]:
    """Compare the PR head with its merge base, excluding base-only changes."""
    return ["git", "diff", "--no-renames", "--name-only", "-z", f"{base_sha}...HEAD"]


def main() -> int:
    tasks = sorted(path for path in Path("tasks").iterdir()
                   if path.is_dir() and (path / "task.toml").is_file())
    if os.environ["EVENT_NAME"] == "pull_request":
        diff = subprocess.run(
            diff_command(os.environ["PR_BASE_SHA"]),
            check=True, stdout=subprocess.PIPE,
        )
        selected = set(select_runtime(os.fsdecode(diff.stdout).split("\0"), [p.name for p in tasks]))
    else:
        selected = {path.name for path in tasks}

    rows = []
    failed = False
    with tempfile.TemporaryDirectory() as temporary:
        for task in tasks:
            report = Path(temporary) / "report.json"
            report.unlink(missing_ok=True)
            command = ["honestenv", "check", str(task), "--out", str(report)]
            if task.name not in selected:
                command.append("--static-only")
            result = subprocess.run(command, check=False)
            failed |= result.returncode != 0
            gates = {}
            if report.exists():
                gates = {gate["name"]: gate["passed"] for gate in json.loads(report.read_text())["gates"]}
            def status(name: str) -> str:
                return "passed" if gates.get(name) is True else "failed"
            runtime = ("skipped" if task.name not in selected else
                       "passed" if gates.get("oracle") is True and gates.get("nop") is True else "failed")
            safe_name = task.name.replace("|", "&#124;").replace("\n", " ")
            rows.append(f"| {safe_name} | {status('schema')} | {status('lint')} | {status('factory')} | {runtime} |")
    summary = f"{len(selected)} of {len(tasks)} tasks selected for runtime. " + ("Checks failed." if failed else "Checks passed.")
    content = "<!-- honestenv-checkup -->\n## honestenv checkup\n\n" + summary + "\n\n| Task | Schema | Lint | Factory | Runtime |\n| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    Path(os.environ["REPORT_PATH"]).write_text(content, encoding="utf-8")
    print(content)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
