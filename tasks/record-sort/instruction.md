# Repair record sorting

Repair `sort_records(records)` in `/app/records.py` in place using only the
Python standard library. Each record is a dictionary with string keys `name`
and `qty`. The name is a string and the quantity is a non-negative integer
written as a decimal string without a sign.

Return a new list ordered by quantity descending as an integer, then by name
ascending in ordinary Python string order. Records equal on both keys retain
their original relative order. Leave the corrected source at `/app/records.py`.
