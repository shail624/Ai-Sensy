"""Storage foundation (Doc 08 §14, FR-MED-06/09).

Pluggable binary storage: the database stores **metadata + a reference, never blobs**. A local
volume is the default backend; an S3-compatible backend can be registered without touching
callers. Access is only ever via signed, expiring URLs.
"""

# Registering the default backend belongs to the package, not to one caller.
#
# `local` registers itself as an import side effect. That import used to live only in
# `app.main`, so the backend existed in the API process and nowhere else — a Celery worker
# imports `app.queue.celery_app` and the task modules, never `app.main`. Every worker-side write
# therefore failed with "storage backend 'local' is not available; registered: ()", which meant
# exports, report exports and inbound media downloads all failed in the deployed stack while the
# API happily served the same code path. Importing it here makes the invariant the docstring
# already claims — "a local volume is the default backend" — true for every process.
#
# Safe against circular imports: `base` and `signing` import nothing from this package.
from app.storage import local as _local_backend  # noqa: F401,E402
