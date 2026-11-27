# Repair text normalization

Repair the package at `/app/textnorm/` in place using only the Python standard
library. `collapse_spaces(text)` in `textnorm.spaces` collapses every run of
whitespace recognized by `str.split()` to one ASCII space and strips leading and
trailing whitespace. `fold_case(text)` in `textnorm.case` applies Unicode
`str.casefold()`.

`normalize(text)` must be exported from `textnorm` so that
`from textnorm import normalize` works. It first calls `collapse_spaces`, then
`fold_case`, and returns the result. Leave the corrected sources at
`/app/textnorm/__init__.py`, `/app/textnorm/spaces.py`, and
`/app/textnorm/case.py`.
