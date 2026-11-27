# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- `honestenv init <org/task>` creates a task skeleton, and `honestenv check --static-only` runs checks without Docker.
- Rejection fixtures in `tests/fixtures/bad_tasks/` that check factory gates without adding tasks to the shipped pack.
- Static factory checks for image pins, verifier isolation and timeout headroom, agent network and user policy, test network access, and reward script quality.
- The `version-compare` program-repair task.
- Collaboration and hygiene files: `.gitignore`, contributing and security guidance, a code of conduct, issue and pull request templates, and project URLs.

### Changed

- Both shipped tasks use a no-network environment policy.
- CI uses `actions/checkout@v7` and `actions/setup-python@v7` and runs official Docker-backed gates in a separate runtime job.

## 0.0.0

### Added

- Static gates for Harbor schema 1.4 and Harbor lint.
- Docker-backed runtime gates for oracle and empty agents.
- The `reservation-window` task.
- CLI commands to check tasks, run gates, and pack tasks.
- CI for unit tests and static gates.
