from datetime import date as calendar_date, timedelta

def add_days(date, days):
    year, month, day = map(int, date.split('-'))
    return (calendar_date(year, month, day) + timedelta(days=days)).isoformat()
