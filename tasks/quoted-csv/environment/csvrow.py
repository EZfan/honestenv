def parse_csv_row(line):
    return line.split(",")


def parse_csv(text):
    return [parse_csv_row(line) for line in text.splitlines()]
