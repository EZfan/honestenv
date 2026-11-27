# Repair version comparison

Fix `cmp_version(left, right)` in `/app/version.py`. Each argument is a
string of one or more non-negative integer components separated by dots,
such as `1`, `1.9`, or `1.10.0`.

Compare components numerically from left to right. Treat missing trailing
components as zero, so `1.2` and `1.2.0` are equal. Return `-1` when `left`
is less than `right`, `0` when they are equal, and `1` when `left` is greater.
For example, `1.10` is greater than `1.9`.

Fix the function in place, preserving its name and argument order. Leave the
corrected source at `/app/version.py`. Use only the Python standard library.
