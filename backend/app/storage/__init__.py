"""Storage foundation (Doc 08 §14, FR-MED-06/09).

Pluggable binary storage: the database stores **metadata + a reference, never blobs**. A local
volume is the default backend; an S3-compatible backend can be registered without touching
callers. Access is only ever via signed, expiring URLs.
"""
