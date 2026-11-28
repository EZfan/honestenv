# Real-path behavior acceptance

Run the fixed batch from the repository root with Python 3.12+, honestenv and Harbor 0.27.0 installed, Docker Compose available to Docker, and the intended Docker daemon selected:

```sh
PATH="$PWD/.venv/bin:$PATH" TMPDIR=/private/tmp DOCKER_HOST=unix:///Users/wangcai2/.colima/honestenv/docker.sock .venv/bin/python scripts/accept_behavior_cases.py /private/tmp/honestenv-w08-acceptance
```

The destination must not exist. The script makes a temporary copy of `tasks/version-compare` for each case and executes the oracle agent through Harbor's Docker backend. The oracle installs the submitted implementation at `/app/version.py`; the shipped separate verifier then grades that file. Two independently written correct variants test numeric ordering and trailing-zero equivalence. Three near-correct implementations test lexical ordering, trailing-zero handling, and omitted components; two more test submission early exit and exceptions. Four cases replace the verifier with a deliberately broken one: missing reward, non-finite reward, nonzero early exit, and exception. These use the reference solution and expect an execution error with no conclusion.

Each case retains a W07 task snapshot, replay metadata, captured streams and W06 report in its named directory, including successful cases for inspection. `batch.json` collects the W06 records. The script exits nonzero if a case cannot be recorded, a result differs from its expected status and conclusion, or a broken-verifier case lacks the expected Harbor exception in its captured output. Replay an individual pack with `honestenv replay PACK`; replay returns the raw reward and must be compared with its report. The batch is a fixed regression sample for one task, not an exhaustive proof of verifier correctness. Broken-verifier cases exercise the actual Harbor path and classification, but an infrastructure failure can also produce an execution error; inspect captured streams before attributing a cause.
