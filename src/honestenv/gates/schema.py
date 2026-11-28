import tomllib

from ..types import GateReport, TaskPackage


def check_schema(package: TaskPackage) -> GateReport:
    return _check_schema(package, audit=False)


def check_audit_schema(package: TaskPackage) -> GateReport:
    return _check_schema(package, audit=True)


def _check_schema(package: TaskPackage, *, audit: bool) -> GateReport:
    root = package.root
    for relative_path in ("instruction.md", "task.toml", "tests/test.sh", "solution/solve.sh"):
        if not (root / relative_path).is_file():
            return GateReport("schema", False, f"Missing {relative_path}")

    if audit:
        for relative_path in ("tests/test.sh", "solution/solve.sh"):
            try:
                (root / relative_path).read_bytes()
            except OSError:
                return GateReport("schema", False, f"Cannot read {relative_path}")

    try:
        instruction = (root / "instruction.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return GateReport("schema", False, "Cannot read instruction.md")
    if not instruction.strip():
        return GateReport("schema", False, "instruction.md is empty")

    try:
        with (root / "task.toml").open("rb") as task_file:
            config = tomllib.load(task_file)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return GateReport("schema", False, "Cannot parse task.toml")

    version = config.get("schema_version")
    if audit:
        supported = {"1", "1.0", "1.1", "1.2", "1.3", "1.4", "2.0"}
        if version is not None and (type(version) not in (str, int, float) or str(version) not in supported):
            return GateReport("schema", False, f"Unsupported schema_version: {version!r}")
    elif version != "1.4":
        return GateReport("schema", False, 'schema_version must be "1.4"')

    if not (root / "environment/Dockerfile").is_file():
        environment = config.get("environment", {})
        docker_image = environment.get("docker_image") if isinstance(environment, dict) else None
        if not isinstance(docker_image, str) or not docker_image.strip():
            return GateReport("schema", False, "Missing environment/Dockerfile or environment.docker_image")

    if not audit and "verifier" in config:
        verifier = config["verifier"]
        if not isinstance(verifier, dict) or verifier.get("environment_mode") != "separate":
            return GateReport("schema", False, 'verifier.environment_mode must be "separate"')

    if audit:
        return GateReport("schema", True, f"Task schema is valid; schema_version: {version if version is not None else 'missing'}")
    return GateReport("schema", True, "Task schema is valid")
