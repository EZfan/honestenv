def add_days(date, days):
    year, month, day = map(int, date.split("-"))
    day += days
    while day > 30:
        day -= 30
        month += 1
    while day < 1:
        day += 30
        month -= 1
    return f"{year:04d}-{month:02d}-{day:02d}"
