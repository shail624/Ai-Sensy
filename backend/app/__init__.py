"""WhatsApp Business Platform backend application package.

Implements the frozen architecture (Docs 01–12). Layering (Doc 01 §2.6):
API (``app.api``) → Services (``app.services``) → Repositories (``app.repositories``)
→ Models (``app.models``), over shared infrastructure in ``app.core`` and ``app.db``.
"""

__version__ = "0.1.0"
