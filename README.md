# honestenv

[English](README.md) | [简体中文](README.zh-CN.md)

Verifiable agent tasks, checked before they ship.

honestenv is a Harbor-compatible factory for verifiable agent tasks. Its core is
quality gates and owned task packs, not an agent framework.

[![CI](https://github.com/EZfan/honestenv/actions/workflows/ci.yml/badge.svg)](https://github.com/EZfan/honestenv/actions/workflows/ci.yml) ![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue) ![Python >=3.12](https://img.shields.io/badge/python-%3E%3D3.12-blue) ![Harbor 0.27.0](https://img.shields.io/badge/Harbor-0.27.0-blue)

Checkable training and evaluation tasks are scarce. [Harbor](https://docs.harborframework.com/) provides the task format and runtime; honestenv owns the gates that check tasks and the packs that contain them.

## Quickstart

With Python 3.12 or newer, install the published package with either:

```sh
pip install honestenv
```

```sh
uv tool install honestenv
```

Create a task skeleton and run its static gates:

```sh
honestenv init my-org/my-task
honestenv check tasks/my-task --static-only
```

The generated task is local to your current directory. Full checks require Docker and Docker Compose.

## Checkout examples

The wheel does not include the repository task pack. After 0.1.1 is released, check out its tag to use the versioned examples:

```sh
git clone --branch v0.1.1 https://github.com/EZfan/honestenv.git
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
honestenv verify-pack dataset
```

The original deterministic tasks are [`tasks/reservation-window`](tasks/reservation-window), [`tasks/version-compare`](tasks/version-compare), [`tasks/invoice-cents`](tasks/invoice-cents), [`tasks/cut-field`](tasks/cut-field), [`tasks/bind-config`](tasks/bind-config), [`tasks/quoted-csv`](tasks/quoted-csv), [`tasks/text-normalize`](tasks/text-normalize), [`tasks/record-sort`](tasks/record-sort), [`tasks/job-order`](tasks/job-order), and [`tasks/date-shift`](tasks/date-shift). All use Harbor schema 1.4. Their verifiers run submitted code in unprivileged subprocesses and check its returned results before awarding a reward.

## CLI

- `honestenv init <org/task> [--force]` writes a task skeleton to `tasks/<task>` in the current directory and records `org/task` as the task name. Each component must start with a letter or digit and contain only ASCII letters, digits, dots, hyphens, and underscores. Neither component may contain `..`. An existing empty directory can be used. A non-empty destination requires `--force`, which may overwrite its files.
- `honestenv check <task-dir> [--static-only] [--out report.json]` runs schema checks, factory policy checks, `harbor lint --extend-select ALL`, and official Docker-backed `harbor run` checks. The built-in solution agent (`-a oracle`) must return a valid reward of exactly 1.0, and the empty agent (`-a nop`) must return a valid reward of exactly 0.0. With `--static-only`, it skips the runtime checks. The command optionally writes a JSON report.
- `honestenv test-gates [--static-only]` runs the same checks for every task under `tasks/`. With `--static-only`, it runs schema, factory policy, and lint checks.
- `honestenv pack <task-dir> --into <dataset-dir>` creates a private snapshot, runs the full check on it, and copies that checked snapshot into the dataset. It rejects symbolic links and special files and preserves ordinary file permissions, including executable bits. It refuses to pack if checks fail or if the destination task directory already exists. It writes or updates `dataset-manifest.json` in the dataset. Use one pack writer per dataset. An interruption between moving the task and updating the manifest can leave an unlisted task, which `verify-pack` rejects.
- `honestenv verify-pack <dataset-dir>` checks the manifest, task hashes, schema versions, and unlisted task directories without running Harbor or Docker. The recorded tool version is provenance and need not match the running version.

The manifest is a JSON object with a `tasks` object keyed by task directory name.
Each entry contains `content_sha256`, `schema_version`, `checked_at` (UTC
ISO-8601 ending in `Z`), and `honestenv_version`. The content hash is SHA-256
over task files in sorted relative POSIX path order. For each file, the UTF-8
path and file bytes are each preceded by their length as an 8-byte big-endian
integer. The digest is lowercase hexadecimal. Compare a check report’s `package.content_hash` to the manifest entry to check that they describe the same file content. The hash does not include permissions, empty directories, images, runtime, or network configuration. Packing checks the snapshot’s permissions and content for changes during the check.

## CI

Repositories with tasks in `tasks/` can call the reusable workflow. Replace both
`<ref>` values with the same commit SHA or tag of this repository:

```yaml
jobs:
  honestenv:
    permissions:
      contents: read
      pull-requests: write
    uses: EZfan/honestenv/.github/workflows/honestenv-check.yml@<ref>
    with:
      honestenv-ref: <ref>
```

The workflow checks out the caller's repository and the specified honestenv ref.
Its `test` job installs honestenv and runs static gates on all shipped tasks.
To run caller tests as well, set the optional `test-command` input to a shell command,
for example `python -m unittest discover -s tests -v`. Its `runtime` job runs official
Docker-backed Harbor gates. On pull requests it compares changes since the merge base with the base SHA:
changes under a shipped `tasks/<name>/` select that task; changes under `src/`,
`pyproject.toml`, `.github/workflows/`, or `.github/actions/` select all tasks.
Other changes skip runtime gates. Pushes to main run all tasks. Only directories
under `tasks/` containing `task.toml` are shipped tasks; canary fixtures are not.

On pull requests, the runtime job posts or updates a Markdown checkup with each
task's schema, lint, factory, and runtime results. Unchanged tasks have runtime
marked skipped. It uses the default `GITHUB_TOKEN`; grant `contents: read` and
`pull-requests: write` to the calling job. Fork pull requests may receive a
read-only token, so their checkup comment may be unavailable. Comment publication
failures produce a warning and do not change the task-check result.

A reusable workflow's checks are named `<caller-job> / test` and
`<caller-job> / runtime`. To keep exact check names `test` and `runtime`, compose
the actions as steps in your own jobs instead:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: EZfan/honestenv/.github/actions/test@<ref>
  runtime:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: EZfan/honestenv/.github/actions/runtime@<ref>
```

Use a commit SHA or tag for each `<ref>`. The runtime action requires full Git
history to compare the PR base. This repository uses these composite actions in
its own `test` and `runtime` jobs. A standalone action repository may come later.

## Factory policy

Factory checks require digest-pinned images in Dockerfiles and `environment.docker_image`, an explicit separate verifier, a non-root agent user, and a restricted agent network policy. Set `environment.network_mode` to `"no-network"`, or use a non-empty restricted allowlist. The agent can override the environment policy. Dockerfiles must not use host networking, and test material must not fetch from public hosts. Reward scripts are checked for obvious unconditional rewards, failure exits, nondeterminism, and missing checks of packaged artifacts. These static checks are heuristics and can produce false positives, including for comments containing `date`. Passing them does not prove a verifier is correct. Runtime gates check the oracle and empty agent, not every possible solution.

The intentionally invalid packages in `tests/fixtures/bad_tasks/` verify that the
factory gates reject bad tasks. They are not part of the shipped `tasks/` pack.

The Headroom Policy requires an explicit, finite `verifier.timeout_sec` of at least 15 seconds. If `metadata.expected_oracle_runtime_sec` is a finite positive number, the timeout must also be at least three times that value.

## Status

Version 0.1.1 includes static and Docker-backed runtime gates, task initialization, packing and pack verification, incremental CI checks, and ten shipped tasks.

To prepare a release, run CI on the exact commit, then create a `v0.1.1` tag at that commit and use the 0.1.1 changelog section as the GitHub Release notes. The `publish.yml` workflow checks that CI succeeded on a main-branch push for the checked-out commit, builds the distributions, and smoke-tests the wheel in a clean environment before publishing through the `pypi` Trusted Publisher environment. The release tag, CI commit, release notes, and published distributions must refer to the same version and commit. Publishing does not verify Docker-backed checks.

## License

[Apache-2.0](LICENSE).

## Project links

[Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md) | [Security](SECURITY.md) | [Code of Conduct](CODE_OF_CONDUCT.md)
