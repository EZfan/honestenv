def order_jobs(jobs):
    ordered = []
    for job in jobs:
        if not job["needs"] or job["needs"][0] in ordered:
            ordered.append(job["id"])
    return ordered
