"""Version 1 records for binary-reward case replay."""

import json
import math
from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class Case:
    case_id: str
    case_version: str
    task_id: str
    task_version: str
    spec_ref: str
    spec_sha256: str
    artifact_refs: tuple[str, ...]
    expected: Literal["must_pass", "must_fail", "unknown"]
    label_basis: str

    def __post_init__(self):
        if self.expected not in ("must_pass", "must_fail", "unknown"):
            raise ValueError("invalid expected label")
        if not all((self.case_id, self.case_version, self.task_id, self.task_version,
                    self.spec_ref, self.spec_sha256, self.artifact_refs, self.label_basis)):
            raise ValueError("case fields must not be empty")


@dataclass(frozen=True)
class BinaryProfile:
    check_config_version: str
    pass_reward: float
    fail_reward: float

    def __post_init__(self):
        if not self.check_config_version:
            raise ValueError("check configuration version is required")
        if any(type(value) not in (int, float) or (type(value) is float and not math.isfinite(value))
               for value in (self.pass_reward, self.fail_reward)):
            raise ValueError("reward mappings must be finite numbers")
        if self.pass_reward == self.fail_reward:
            raise ValueError("reward mappings must be distinct")


@dataclass(frozen=True)
class Run:
    case: Case
    profile: BinaryProfile
    run_status: Literal["graded", "execution_error", "unsupported", "skipped"]
    conclusion: Literal["pass", "fail"] | None
    reward_raw: str | None
    reward_valid: bool
    invalid_reason: str | None
    harbor_version: str
    honestenv_version: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if self.run_status not in ("graded", "execution_error", "unsupported", "skipped"):
            raise ValueError("invalid run status")
        if not self.harbor_version or not self.honestenv_version:
            raise ValueError("tool versions are required")
        if self.run_status == "graded":
            if not self.reward_valid or self.conclusion not in ("pass", "fail") or self.invalid_reason is not None:
                raise ValueError("graded runs require a valid reward and conclusion")
            try:
                reward = json.loads(self.reward_raw)
            except (TypeError, ValueError) as error:
                raise ValueError("graded runs require a raw reward") from error
            expected = self.profile.pass_reward if self.conclusion == "pass" else self.profile.fail_reward
            if (type(reward) not in (int, float)
                    or (type(reward) is float and not math.isfinite(reward)) or reward != expected):
                raise ValueError("conclusion does not match profile")
        elif self.reward_valid or self.conclusion is not None or not self.invalid_reason:
            raise ValueError("ungraded runs require a reason and no conclusion")


def record_reward(case: Case, profile: BinaryProfile, result: dict, *,
                  harbor_version: str, honestenv_version: str,
                  evidence_refs: tuple[str, ...] = ()) -> Run:
    """Interpret one Harbor trial using a profile fixed by the caller before execution."""
    verifier = result.get("verifier_result")
    rewards = verifier.get("rewards") if isinstance(verifier, dict) else None
    present = isinstance(rewards, dict) and "reward" in rewards
    value = rewards["reward"] if present else None
    raw = json.dumps(value, ensure_ascii=False, allow_nan=True) if present else None
    if not present:
        reason = "missing_reward"
    elif result.get("reward_valid") is not True:
        reason = "harbor_reward_invalid"
    elif type(value) not in (int, float):
        reason = "invalid_reward_type"
    elif type(value) is float and not math.isfinite(value):
        reason = "non_finite_reward"
    elif value not in (profile.pass_reward, profile.fail_reward):
        reason = "unmapped_reward"
    else:
        reason = None
    return Run(case, profile, "execution_error" if reason else "graded",
               None if reason else ("pass" if value == profile.pass_reward else "fail"),
               raw, reason is None, reason, harbor_version, honestenv_version, evidence_refs)


@dataclass(frozen=True)
class Report:
    runs: tuple[Run, ...]
    schema_version: str = "1.0"

    def __post_init__(self):
        if self.schema_version != "1.0":
            raise ValueError("unsupported report schema version")

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, allow_nan=False, indent=2)
