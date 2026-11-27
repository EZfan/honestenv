# Repair reservation window membership

The function `is_reserved(minute, start, end)` in
`/app/reservation.py` decides whether a minute falls within a reservation.

A reservation starts at minute `start` and ends just before minute `end`.
The start is included, but the end is excluded. A zero-length reservation
contains no minutes.

All three arguments are integers with `0 <= start <= end <= 1440` and
`0 <= minute <= 1440`. Return a Boolean.

For example, for a reservation from minute 60 to minute 90, minute 60 is
reserved and minute 90 is not.

Fix the function in place, preserving its name and argument order. Leave the
corrected source at `/app/reservation.py`. Use only the Python standard library.
