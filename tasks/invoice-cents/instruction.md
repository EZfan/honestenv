# Repair invoice arithmetic

Repair both `/app/money.py` and `/app/invoice.py` in place. Use only the
Python standard library and integer arithmetic.

`parse_cents(text)` in `money.py` accepts a non-negative dollar amount with a
decimal point and exactly two digits after it, with no currency symbol or
thousands separators. Return its integer number of cents. For example,
`parse_cents("1.13")` returns `113`.

`line_total(unit_cents, quantity)` in `invoice.py` returns the product of its
integer arguments. `invoice_total(lines)` returns the sum of the line totals
for a list of `(unit_cents, quantity)` pairs; an empty list totals zero.
Leave the corrected sources at `/app/money.py` and `/app/invoice.py`.
