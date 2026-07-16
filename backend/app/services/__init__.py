"""Service layer — application/business logic and transaction boundaries (Doc 01 §2.6).

Services orchestrate repositories, own the unit-of-work (commit/rollback), and enforce the
rules in Docs 01/04. Endpoints call services; services call repositories.
"""
