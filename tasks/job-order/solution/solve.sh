#!/bin/sh
set -eu
cat > /app/jobs.py <<'PYCODE'
from collections import deque


def order_jobs(jobs):
    ids = {job["id"] for job in jobs}
    prerequisites = {job["id"]: set(job["needs"]) for job in jobs}
    if any(not needs <= ids for needs in prerequisites.values()):
        raise ValueError("missing prerequisite")
    ready = deque(job["id"] for job in jobs if not prerequisites[job["id"]])
    ordered = []
    while ready:
        completed = ready.popleft()
        ordered.append(completed)
        for job in jobs:
            needs = prerequisites[job["id"]]
            if completed in needs:
                needs.remove(completed)
                if not needs:
                    ready.append(job["id"])
    if len(ordered) != len(jobs):
        raise ValueError("cycle")
    return ordered
PYCODE
