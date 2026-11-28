# Verifier comparison

Run from the repository root with Harbor 0.27.0 and Docker available:

```sh
PATH="$PWD/.venv/bin:$PATH" TMPDIR=/private/tmp DOCKER_HOST=unix:///Users/wangcai2/.colima/honestenv/docker.sock .venv/bin/python scripts/compare_verifiers.py /private/tmp/honestenv-w09-comparison
```

The destination must be new. `--before` and `--after` can select other `tests/test.sh` scripts for this task; all other task files and submissions remain fixed. The defaults compare the saved previous verifier with the current verifier, which adds third-component ordering checks. The fixed cases include the reference solution, two valid variants, and a wrong implementation that treats unequal nonzero single-digit third components as equal. The command fails on ungraded runs, an after result that disagrees with a label, or a valid case that did not pass before. A target that was already rejected before and remains rejected is accepted.

`comparison.json` records script hashes, each result, changes and the acceptance decision. Each result links to a W07 evidence pack containing the exact task snapshot, W06 report and replay metadata; `honestenv replay PACK` reruns it. This finite case set does not establish general verifier correctness.
