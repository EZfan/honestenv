# honestenv

Verifiable agent tasks, checked before they ship.

honestenv is a Harbor-compatible factory for verifiable agent tasks. Its core is
quality gates and owned task packs, not an agent framework.

[![CI](https://github.com/EZfan/honestenv/actions/workflows/ci.yml/badge.svg)](https://github.com/EZfan/honestenv/actions/workflows/ci.yml) ![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue) ![Python >=3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue) ![Harbor 0.27.0](https://img.shields.io/badge/Harbor-0.27.0-blue)

Checkable training and evaluation tasks are scarce. [Harbor](https://docs.harborframework.com/) provides the task format and runtime; honestenv owns the gates that check tasks and the packs that contain them.

## Quickstart

With Python 3.12 or newer, clone the repository and install the package:

```sh
git clone https://github.com/EZfan/honestenv.git
cd honestenv
pip install -e .
```

Run the static gates on all local tasks:

```sh
honestenv test-gates --static-only
```

Full checks require Docker and Docker Compose. Check the first task and copy it into a new dataset directory:

```sh
honestenv check tasks/reservation-window --out report.json
honestenv pack tasks/reservation-window --into dataset
```

The first task, [`tasks/reservation-window`](tasks/reservation-window), is a small original deterministic program-repair task in Harbor schema 1.4.

## CLI

- `honestenv check <task-dir> [--out report.json]` runs schema checks, `harbor lint --extend-select ALL`, and official Docker-backed `harbor run` checks. The built-in solution agent (`-a oracle`) must return a valid reward of exactly 1.0, and the empty agent (`-a nop`) must return a valid reward of exactly 0.0. The command optionally writes a JSON report.
- `honestenv test-gates [--static-only]` runs the same checks for every task under `tasks/`. With `--static-only`, it runs only schema and lint checks.
- `honestenv pack <task-dir> --into <dataset-dir>` runs the full check, including runtime gates, and copies the task into the dataset. It refuses to pack if checks fail or if the destination task directory already exists.

## Status

Version 0.0.0 includes static gates for Harbor schema 1.4 and `harbor lint --extend-select ALL`, plus Docker-backed runtime gates. CI runs the static gates only. Docker is not yet used on GitHub Actions.

## License

[Apache-2.0](LICENSE).
