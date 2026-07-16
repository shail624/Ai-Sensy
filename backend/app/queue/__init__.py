"""Queue Engine (Doc 06) — Celery application, worker framework, registry, retry and DLQ.

This package is the generic async fabric. Domain tasks (sends, webhooks, imports, exports,
AI, …) are registered by their own modules; nothing here knows about them.
"""
