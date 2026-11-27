from dataclasses import dataclass
from pathlib import Path


@dataclass
class TaskPackage:
    root: Path
    content_hash: str


@dataclass
class GateReport:
    name: str
    passed: bool
    details: str


@dataclass
class CheckReport:
    package: TaskPackage
    gates: list[GateReport]
    passed: bool


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
