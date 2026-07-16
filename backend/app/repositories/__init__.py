"""Repository layer — the only place that builds queries against the ORM (Doc 01 §2.6).

Services depend on repositories, never on raw SQLAlchemy, so persistence concerns stay
isolated and swappable (clean architecture). Repositories flush but do **not** commit;
transaction boundaries belong to the service/unit-of-work (Doc 01 §2.6).
"""
