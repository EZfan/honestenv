from .. import harbor_cli
from ..types import GateReport, TaskPackage


def check_agent(package: TaskPackage, *, agent: str, expected_reward: float) -> GateReport:
    result = harbor_cli.run(package.root, agent=agent)
    if result.returncode != 0:
        details = f"Harbor exited with status {result.returncode}: {result.stderr or result.stdout}"
        return GateReport(agent, False, details)
    if result.reward is None:
        return GateReport(agent, False, "Missing or invalid reward")
    return GateReport(
        agent,
        result.reward == expected_reward,
        f"Reward {result.reward}; expected {expected_reward}",
    )
