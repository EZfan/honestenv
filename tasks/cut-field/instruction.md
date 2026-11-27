# Repair field extraction

Fix the executable `/app/cutfield` in place. Use only the Python standard
library. Its usage is `cutfield -d DELIM -f N FILE`, where `DELIM` is a
single-character delimiter and `N` is a positive, 1-based field index.

For each line in FILE, print the Nth field followed by a newline, without an
added delimiter. If the line has fewer than N fields, print an empty line.
Exit 0 on success. Exit 1 if FILE is missing or the flags are invalid, including
missing `-d` or `-f`, an invalid delimiter, or N that is not a positive integer.
Leave the corrected executable at `/app/cutfield`.
