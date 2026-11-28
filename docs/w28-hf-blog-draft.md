# Beyond oracle=1 and nop=0: Catching Real Verifier Shortcuts in Public Harbor and Terminal-Bench Tasks

*Draft for the Hugging Face Community Blog. Findings describe pinned snapshots, not necessarily current upstream behavior.*

A reference solution that earns 1 and an empty agent that earns 0 are valuable checks. They do not tell us whether an incorrect artifact between those extremes also earns 1. We tested that boundary using concrete counterexamples against original public task verifiers. In one case, a C/Python Fibonacci program returned `999` for `F(2)` and still earned full reward; in another, an async implementation never called the supplied job and passed by printing expected output.

These are targeted, reproducible observations, not a benchmark leaderboard or a prevalence estimate. The tasks were a convenience sample, and the Harbor examples are illustrative tasks. The experiments do not show that an evaluated agent discovered or exploited these shortcuts. We have not tested an upstream fix or obtained independent upstream confirmation.

## What we ran

We used [Harbor's example tasks at `cf4bd0043f4e3a91847edf1b799343caf74cf182`](https://github.com/harbor-framework/harbor/tree/cf4bd0043f4e3a91847edf1b799343caf74cf182/examples/tasks) and [Terminal-Bench 2.1 at `3e235dff6880252a587fa479c09bcb1e16edf2eb`](https://huggingface.co/datasets/harborframework/terminal-bench-2.1/tree/3e235dff6880252a587fa479c09bcb1e16edf2eb/tasks). The reported rewards come from the original verifier scripts executed in Docker against selected candidate artifacts; these direct executions are not Harbor trials. We compared the result with the task instruction and included controls where documented. Dependencies and images were resolved at runtime, so the task revision alone does not freeze the execution environment.

For the three Harbor examples, full `honestenv check` runs separately produced oracle = 1 and nop = 0, although their overall checks failed static profile gates. The same baseline held for `polyglot-c-py`; its overall check also failed schema, lint and factory gates. Static profile incompatibility is not a semantic detection of the counterexamples. For the selected round-5 Terminal-Bench tasks, the replay reports also record oracle = 1 and nop = 0.

## What the counterexamples exposed

| Pinned task | Candidate and observed result | What the result establishes |
| --- | --- | --- |
| `hello-workdir` | `/custom-workdir/NOT-THE-PWD` earned 1. | An unanchored `grep` accepts the required path as a substring. |
| `hello-user` | `not-agent` and `NOT Hello, world!` earned 1 together. | Both unanchored matches accept incorrect contents. |
| `hello-healthcheck` | `not ok, nothing fetched` earned 1. | The match accepts `ok` inside unrelated text. The replay did not start the server or establish that a request occurred. |
| `polyglot-c-py` | Both implementations returned `999` for input 2, but earned 1; `F(2)` should be 1. | The verifier checks inputs 0, 10 and 42, leaving this concrete incorrect behavior untested. |
| `cancel-async-tasks` | A candidate printed fixed expected strings, slept, and fabricated cleanup output without calling the supplied job; reward 1. | A separate callable recorded zero calls. An immediate-return candidate received 0. |
| `chess-best-move` | `e2e4 g2g4` on one line earned 1. | The instruction asks for one move per line; whitespace splitting accepts this format boundary. A one-move file received 0. |
| `regex-log` | A regex listing nine expected dates earned 1, despite extracting `2025-01-09` from a separate line without an IP. | The fixed sample permits overfitting and does not establish the requested IP condition. |
| `sqlite-db-truncate` | A candidate that never opened the database wrote seven reference tuples and one invented row; reward 1. | The set-intersection threshold accepts the missing and fabricated rows together. Six correct rows received 0. |

The three Harbor instances share one substring-matching mechanism; they are not three independent vulnerability classes. The chess observation concerns the requested format, not a claim that providing the known answers for this fixed board is itself a defect. The SQLite probe does not establish the maximum number of recoverable rows.

The `openssl-selfsigned-cert` replay report describes four requirement gaps, each receiving reward 1: a mismatched key and certificate; an invalid combined PEM containing a literal `PRIVATE KEY` marker and certificate; a fabricated verification report; and a script that prints fixed success text without checking the certificate. The mismatch candidate also replaced the checking script, so it does not independently establish acceptance with a genuine checking script. These are four reproducible gaps as recorded in the report, not four independent exploit chains. Empty certificate output, a missing script, and a 364-day certificate each received 0. The specified local round-5B directory contains the report and replay script but no retained replay log; the report records that initial quoting errors were corrected before the final mismatch and fake-script results. This limits independent inspection of those recorded runs.

## Negative results belong in the record

For `log-summary-date-ranges`, the tested empty CSV, partial CSV and incorrect count were rejected: no false acceptance was confirmed in those probes. That is not a proof of correctness across all inputs.

A separate bounded probe of [`gsm8k-harbor` at `39b9ebc6c7d5631922e9e98d0f4ca8708bcdf533`](https://huggingface.co/datasets/steinwang/gsm8k-harbor/tree/39b9ebc6c7d5631922e9e98d0f4ca8708bcdf533) found zero confirmed verifier defects. Ten consecutive instances received 50 direct probes, and all ten shared one grader implementation. The probes tested gold, malformed, different numeric, oversized and missing outputs; they did not validate every possible answer or the semantic correctness of each gold value. One instance also received a complete oracle/nop check. These negative observations should not be combined with the targeted positive cases into a rate.

## A maintainer-facing repair and regression checklist

The following are **proposed fixes and tests**, not upstream patches or completed post-fix results. Each proposed change needs review against the full task contract and legitimate alternative solutions.

| Case | Proposed verifier change | Regression to run after a patch |
| --- | --- | --- |
| Harbor examples | Compare the complete expected artifact with well-defined newline handling instead of matching substrings. | Reject the three recorded invalid files; retain exact valid and missing-file controls. For healthcheck, decide separately whether the contract requires evidence of a request. |
| Fibonacci | Exercise both language implementations on additional boundary and varied inputs against an independent reference. | Reject the `F(2)=999` candidate and retain the upstream solution. Finite tests still cannot prove correctness for every input. |
| Async tasks | Supply instrumented jobs and assert calls, concurrency and cancellation/cleanup behavior rather than trusting printed messages. | Reject the zero-call candidate and immediate return; accept legitimate implementations with different output timing where the contract allows it. |
| Chess | Check the requested line structure explicitly as well as the moves. | Reject the same-line candidate and missing move; accept valid line endings and order if the instruction permits them. |
| Certificate | Parse and compare actual certificate, private key, combined PEM and generated report; exercise the checker against valid and invalid certificates. | Reject each recorded counterexample, including the combined mismatch and fake script; retain a valid generated certificate and script. |
| Regex | Test independently chosen valid and invalid lines, including absent and invalid IPs and dates. | Reject the fixed-date candidate on the recorded no-IP line and retain valid alternative regexes. |
| SQLite | Compare recovered output against independently established database contents and reject fabricated rows, with the intended recovery criterion made explicit. | Reject the recorded seven-plus-invented artifact; preserve valid recoveries and document the chosen threshold. |

A useful regression suite needs both directions: reject the demonstrated counterexample and preserve valid solutions. No fix has been implemented or validated in these experiments, and these suggestions do not assert maintainer agreement.

## Minimal replay and evidence

The local experiment directories include the copied task snapshots, scripts and reports for their respective rounds. On the machine holding those worktrees, with Docker available, run each command from its corresponding worktree root:

```sh
# feat-w25-audit-r3
bash experiments/w25-round3/replay.sh
# feat-w25-audit-r4; Docker CLI plugin config may be needed (see its REPORT.md)
DOCKER_CONFIG=/tmp/w25r4-docker DOCKER_BUILDKIT=1 bash experiments/w25-round4/replay.sh
# feat-w25-r5a
bash experiments/w25-round5a/replay.sh
# feat-w25-r5b-v2
bash experiments/w25-round5b/replay.sh
# feat-w25-r5c
bash experiments/w25-round5c/replay.sh
```

These paths are local research artifacts, not yet a public portable release. The round-4 report describes creating `/tmp/w25r4-docker/config.json` with the local Docker CLI plugin directory if needed. The scripts default to the local Colima Docker socket; adapt the Docker connection for another host. Builds and verifier dependency installation may need network access. The Harbor healthcheck build uses a temporary Dockerfile compatibility adjustment (`COPY` then `chmod`); the task verifier and assets are unchanged. Round 5A runs cases sequentially in the same container per task, replacing the candidate between cases; rounds 5B and 5C report fresh containers per candidate. For GSM8K, the round-2 report gives the archive URL, SHA-256 and probe commands. The report and logs are evidence of these runs; portability and post-fix replay remain work to complete before publication.

## Where this fits alongside OpenEnv

[`openenv validate`](https://huggingface.co/docs/openenv/reference/cli) already provides validation capabilities, including a Harbor path. The intended role for honestenv is complementary: reproducible behavioral counterexamples, shortcut probes and regression comparisons, rather than a claim to replace existing oracle/nop validation. In the documented local comparison with OpenEnv 0.15.0 and Harbor 0.25.0, some runtime and semantic checks were skipped or not implemented for the tested Harbor binding; `hf-sandbox` was not tested. A skipped or unexecuted check is not a demonstrated miss. The proposed integration is future work, not an implemented plugin or a measured head-to-head advantage.

A verifier is part of the evaluation, and its failures deserve the same versioned evidence as a model result: a task contract, a minimal candidate, an observed reward, controls, and a post-fix regression. These examples show why the next test after oracle and nop can be a carefully chosen wrong answer.
