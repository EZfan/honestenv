# Contributing

Use Python 3.12 or newer. Install the project and run the unit tests and static gates:

```sh
pip install -e .
python -m unittest discover -s tests -v
honestenv test-gates --static-only
```

Docker and Docker Compose are required for the full checks. Run them for one task or for all tasks:

```sh
honestenv check tasks/reservation-window
honestenv test-gates
```

## Add a task

Add a directory under `tasks/` using Harbor schema 1.4. Use [reservation-window](tasks/reservation-window) as an example for the task configuration, instructions, environment, solution, and verifier. Run `honestenv check tasks/<task-name>` before submitting. A task must pass the full gates before `honestenv pack` can pack it.
