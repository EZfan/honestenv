import subprocess

from .. import harbor_cli
from ..types import GateReport, TaskPackage


def check_agent(package: TaskPackage, *, agent: str, expected_reward: float) -> GateReport:
    result = harbor_cli.run(package.root, agent=agent)
    if "unknown flag: --project-name" in result.stderr + result.stdout:
        return GateReport(agent, False, "Docker Compose failed (unknown flag: --project-name); install the Compose plugin and check DOCKER_CONFIG and cliPluginsExtraDirs.")
    if result.returncode != 0:
        details = f"Harbor exited with status {result.returncode}: {result.stderr or result.stdout}"
        return GateReport(agent, False, details)
    if result.reward is None:
        try:
            compose = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, check=False)
        except OSError as exc:
            return GateReport(agent, False, f"Missing or invalid reward; Docker Compose preflight failed: {exc}. Install Docker and the Compose plugin.")
        if compose.returncode != 0 or "unknown flag: --project-name" in result.stderr + result.stdout:
            return GateReport(agent, False, "Docker Compose is unavailable or failed; install the Compose plugin and check DOCKER_CONFIG and cliPluginsExtraDirs. " + (compose.stderr or result.stderr or result.stdout))
        return GateReport(agent, False, "Missing or invalid reward; Harbor may not have started a trial. Inspect Harbor job exceptions and Docker logs. " + (result.stderr or result.stdout))
    return GateReport(
        agent,
        result.reward == expected_reward,
        f"Reward {result.reward}; expected {expected_reward}",
    )
