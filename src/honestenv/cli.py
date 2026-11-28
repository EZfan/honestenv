import argparse
import json
import os
import shutil
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .evidence import replay, run_case
from .gates.baseline import check_baseline
from .gates.lint import check_lint
from .gates.run import check_agent
from .gates.schema import check_schema
from .package import content_hash, load, permissions
from .scaffold import init_task
from .types import CheckReport


def check_task(task_dir: Path, *, static_only: bool = False) -> CheckReport:
    package = load(task_dir)
    original_permissions = permissions(package)
    gates = [check_schema(package), check_lint(package), check_baseline(package)]
    if not static_only:
        gates.extend([
            check_agent(package, agent="oracle", expected_reward=1.0),
            check_agent(package, agent="nop", expected_reward=0.0),
        ])
    if content_hash(package) != package.content_hash or permissions(package) != original_permissions:
        raise ValueError("task content changed during checks")
    report = CheckReport(package, gates, all(gate.passed for gate in gates))
    print(f"{package.root}: {'passed' if report.passed else 'failed'}")
    for gate in gates:
        print(f"  {gate.name}: {'passed' if gate.passed else 'failed'} - {gate.details}")
    return report


def read_manifest(dataset: Path) -> dict:
    path = dataset / "dataset-manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or set(manifest) != {"tasks"} or not isinstance(manifest["tasks"], dict):
            raise ValueError("expected an object with a tasks object")
        for name, entry in manifest["tasks"].items():
            if not isinstance(name, str) or name in ("", ".", "..") or Path(name).name != name or "\\" in name:
                raise ValueError("invalid task directory name")
            if not isinstance(entry, dict) or set(entry) != {"content_sha256", "schema_version", "checked_at", "honestenv_version"}:
                raise ValueError(f"invalid entry for {name}")
            if any(not isinstance(value, str) or not value for value in entry.values()):
                raise ValueError(f"invalid entry for {name}")
            digest = entry["content_sha256"]
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError(f"invalid content hash for {name}")
            timestamp = entry["checked_at"]
            if not timestamp.endswith("Z") or datetime.fromisoformat(timestamp[:-1] + "+00:00").utcoffset() != timezone.utc.utcoffset(None):
                raise ValueError(f"invalid check timestamp for {name}")
        return manifest
    except (OSError, ValueError) as error:
        raise ValueError(f"invalid or missing manifest {path}: {error}") from error


def verify_pack(dataset: Path) -> None:
    manifest = read_manifest(dataset)
    for name, entry in manifest["tasks"].items():
        task = dataset / name
        package = load(task)
        with (task / "task.toml").open("rb") as task_file:
            schema_version = tomllib.load(task_file)["schema_version"]
        if schema_version != entry["schema_version"]:
            raise ValueError(f"schema version mismatch for {name}")
        if package.content_hash != entry["content_sha256"]:
            raise ValueError(f"content hash mismatch for {name}")
    for task in dataset.iterdir():
        if task.is_dir() and (task / "task.toml").is_file() and task.name not in manifest["tasks"]:
            raise ValueError(f"unlisted task directory: {task.name}")
    print(f"{dataset}: verified")


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

    verify_parser = subparsers.add_parser("verify-pack", help="Verify a dataset manifest and its tasks")
    verify_parser.add_argument("dataset_dir", type=Path)

    evidence_parser = subparsers.add_parser("evidence-run", help="Run one case and optionally retain its evidence")
    evidence_parser.add_argument("task_dir", type=Path)
    evidence_parser.add_argument("--out", type=Path, required=True)
    evidence_parser.add_argument("--agent", choices=("oracle", "nop"), required=True)
    evidence_parser.add_argument("--expected", choices=("must_pass", "must_fail", "unknown"), required=True)
    evidence_parser.add_argument("--confirmed-defect", action="store_true")

    replay_parser = subparsers.add_parser("replay", help="Replay one retained case")
    replay_parser.add_argument("pack", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "replay":
            return replay(args.pack)

        if args.command == "evidence-run":
            retained = run_case(args.task_dir, args.out, agent=args.agent, expected=args.expected,
                                confirmed_defect=args.confirmed_defect)
            print("evidence retained" if retained else "evidence not retained")
            return 0

        if args.command == "init":
            print(init_task(args.name, force=args.force))
            return 0

        if args.command == "verify-pack":
            verify_pack(args.dataset_dir)
            return 0

        if args.command == "test-gates":
            tasks_dir = Path("tasks")
            reports = [
                check_task(task_dir, static_only=args.static_only)
                for task_dir in sorted(tasks_dir.iterdir())
                if task_dir.is_dir() and (task_dir / "task.toml").is_file()
            ]
            return 0 if all(report.passed for report in reports) else 1

        if args.command == "check":
            report = check_task(args.task_dir, static_only=args.static_only)
            if args.out is not None:
                args.out.write_text(json.dumps(asdict(report), default=str, indent=2) + "\n", encoding="utf-8")
        else:
            source = load(args.task_dir).root
            with tempfile.TemporaryDirectory(prefix="honestenv-snapshot-") as directory:
                snapshot = Path(directory) / source.name
                shutil.copytree(source, snapshot, symlinks=True)
                load(snapshot)  # Reject links introduced during the copy.
                snapshot_permissions = permissions(load(snapshot))
                report = check_task(snapshot)
                if report.passed:
                    args.into.mkdir(parents=True, exist_ok=True)
                    destination = args.into / source.name
                    if destination.exists() or destination.is_symlink():
                        raise FileExistsError(destination)
                    manifest_path = args.into / "dataset-manifest.json"
                    manifest = read_manifest(args.into) if manifest_path.exists() else {"tasks": {}}
                    with (snapshot / "task.toml").open("rb") as task_file:
                        schema_version = tomllib.load(task_file)["schema_version"]
                    with tempfile.TemporaryDirectory(prefix=".honestenv-pack-", dir=args.into) as staging:
                        staged_task = Path(staging) / source.name
                        shutil.copytree(snapshot, staged_task, symlinks=True)
                        if (load(staged_task).content_hash != report.package.content_hash
                                or content_hash(report.package) != report.package.content_hash
                                or permissions(report.package) != snapshot_permissions
                                or permissions(load(staged_task)) != snapshot_permissions):
                            raise ValueError("snapshot changed after checks")
                        manifest["tasks"][destination.name] = {
                            "content_sha256": report.package.content_hash,
                            "schema_version": schema_version,
                            "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "honestenv_version": __version__,
                        }
                        staged_manifest = Path(staging) / "dataset-manifest.json"
                        staged_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                        os.rename(staged_task, destination)
                        try:
                            os.replace(staged_manifest, manifest_path)
                        except OSError:
                            shutil.rmtree(destination)
                            raise
                    print(destination)
        return 0 if report.passed else 1
    except (OSError, ValueError, KeyError) as error:
        print(f"honestenv: {error}", file=sys.stderr)
        return 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
