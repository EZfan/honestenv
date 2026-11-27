def line_total(unit_cents, quantity):
    return unit_cents


def invoice_total(lines):
    return sum(line_total(unit_cents, quantity) for unit_cents, quantity in lines)
