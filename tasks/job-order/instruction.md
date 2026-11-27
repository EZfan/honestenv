# Repair job ordering

Repair `order_jobs(jobs)` in `/app/jobs.py` in place using only the Python
standard library. Each job is a dictionary with a unique string `id` and a
`needs` list of prerequisite job IDs, which may be empty.

Return a new list of IDs with every prerequisite before the job that needs it,
including transitive dependencies. Among jobs whose remaining prerequisites
are satisfied, use a FIFO queue: enqueue initially ready jobs in input order,
and enqueue newly ready jobs in input order as each job is removed from the
queue. Raise `ValueError` if any prerequisite ID is missing or the graph has a
cycle. Do not mutate the input list or its dictionaries. Leave the corrected
source at `/app/jobs.py`.
