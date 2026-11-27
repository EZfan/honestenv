def sort_records(records):
    return sorted(records, key=lambda record: record["qty"], reverse=True)
