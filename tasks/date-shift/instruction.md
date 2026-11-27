# Repair date shifting

Repair `add_days(date, days)` in `/app/dateshift.py` in place using only the
Python standard library. `date` is a `YYYY-MM-DD` string with zero-padded month
and day, and `days` is a signed integer. Return the date that many days later,
or earlier for a negative value, as a `YYYY-MM-DD` string with zero-padded
month and day. Use the proleptic Gregorian calendar, including month and year
rollover. Leap years are divisible by 4, except century years, which are leap
years only when divisible by 400. Leave the corrected source at
`/app/dateshift.py`.
