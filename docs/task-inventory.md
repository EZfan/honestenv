# Task inventory

These tasks are small repair exercises. Their fixed examples are not exhaustive
specifications, and passing does not establish correctness on every input.

| Task | Intended use | Alternative approach and remaining limits |
| --- | --- | --- |
| reservation-window | Check half-open interval membership. | Negate the two outside conditions; only integer minutes in the stated range are covered. |
| version-compare | Compare numeric version components. | Pad components with zero using `zip_longest`; invalid versions are outside the task. |
| invoice-cents | Parse and total amounts in cents. | Split dollars and cents and sum line products; examples do not rule out floating-point arithmetic. |
| cut-field | Extract a delimited field from each line. | Read lines and split by the delimiter; multi-character delimiters are not tested. |
| bind-config | Repair server bind settings. | Parse TOML with `tomllib`; `app.py` is present in both environment and tests. |
| quoted-csv | Parse quoted CSV rows. | Use the standard-library CSV reader; malformed inputs are not covered. |
| text-normalize | Collapse whitespace and fold case. | Split and join whitespace then use `casefold`; examples cover a small Unicode sample. |
| record-sort | Sort records without changing the input. | Use a stable sort with a numeric quantity key; malformed quantities are outside scope. |
| job-order | Order jobs by dependencies. | Use a queue of ready jobs; examples cover a few graphs. |
| date-shift | Shift Gregorian dates. | Use `datetime.date` and `timedelta`; examples cover selected boundaries. |

The following bad fixtures must fail the static factory check:

| Fixture | Expected rule |
| --- | --- |
| always-reward-one | Reward one must be conditional on a packaged artifact. |
| public-network-tests | Tests must not fetch public hosts. |
| missing-timeout | Verifier timeout must provide headroom. |
| reward-one-nonzero-exit | Reward one must not precede an explicit failure exit. |
| nondeterministic-tests | Test material must avoid nondeterministic tokens. |
| unpinned-image | Images must be digest-pinned. |
| shared-verifier-mode | Verifier must use separate mode. |
| unrestricted-network | Agent network must be restricted. |
| root-agent | Agent must be non-root. |
| never-reward-one | Test script must contain a reward-one write. |

The static checks are heuristics. The host allowlist is currently read only
from `[environment]`. The canary unit test checks static passage for the first
two positive tasks; `test-gates --static-only` checks all ten. The CLI test
hard-codes version `0.1.0`, and package metadata has no authors field.
