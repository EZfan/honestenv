# Repair CSV parsing

Repair `/app/csvrow.py` in place using only the Python standard library.
`parse_csv_row(line)` returns a list of field strings from one CSV line.
Fields are separated by commas. A field may be enclosed in double quotes to
contain commas, and two double quotes inside a quoted field represent one
literal double quote. Quotes close on the same line.

`parse_csv(text)` returns a list of parsed rows, splitting text into lines with
`\n` or `\r\n`. A completely empty line is an empty row (`[]`). An empty text
has no rows, and a final line terminator does not add a row. Leave the corrected
source at `/app/csvrow.py`.
