# honestenv

honestenv is a quality-check CLI for Harbor-compatible task directories. It
requires Python 3.12 or newer and Harbor 0.27.0.

Install locally with `pip install -e .`. Docker and Docker Compose are required
for the runtime gates.

Run `honestenv check tasks/reservation-window` to check the task schema, Harbor
lint, and the Harbor oracle and nop agents. The oracle must receive reward 1.0
and the nop agent must receive reward 0.0. Add `--out report.json` to save the
report.

Run `honestenv test-gates` to check every task in `tasks/`. Add `--static-only`
to run only schema and lint checks. Run `honestenv pack TASK --into DATASET` to
copy a passing task into a dataset.
