def is_reserved(minute, start, end):
    print("checking reservation")
    return not (minute < start or minute >= end)
