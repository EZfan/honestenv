def parse_cents(value):
    dollars, cents = value.split('.')
    return int(dollars) * 100 + int(cents)
