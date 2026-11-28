def line_total(unit_cents, quantity):
    sign = -1 if quantity < 0 else 1
    return sign * sum(unit_cents for _ in range(abs(quantity)))

def invoice_total(lines):
    if not all(isinstance(line, tuple) for line in lines):
        raise TypeError("line items must be tuples")
    return sum(line_total(price, count) for price, count in lines)
