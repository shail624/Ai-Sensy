"""Endpoint-scoped index for provider message identity (QR-00).

Supports the hardened lookup in
:meth:`app.repositories.message.MessageRepository.get_by_provider_message_id`, which resolves a
provider message id **within one endpoint** rather than globally — ADR-0020, "Provider message
identity is scoped by connection/endpoint", and Doc 33 §6.1 "Message identity".

Purely additive and index-only:

* **No column is added and no backfill is performed.** ``messages.organization_id`` and
  ``messages.phone_number_id`` have both been ``NOT NULL`` since ``0016_conversations_messages``,
  so every existing row already carries explicit, authoritative endpoint ownership. Nothing has to
  be derived, inferred, or invented for a second provider to be introduced safely.
* **A UNIQUE index is deliberately *not* created.** ``messages`` is
  ``PARTITION BY RANGE COLUMNS(created_at)`` and MySQL requires every unique key on a partitioned
  table to contain the partitioning columns (error 1503, verified against MySQL 8.0.46 on this
  schema). Adding ``created_at`` to the key would permit the very duplicate this rule exists to
  prevent, so uniqueness stays enforced by the scoped read plus the persist-first ingestion path,
  exactly as it already is for Meta today. This is a recorded architectural limit, not an omission.

The pre-existing ``ix_msg_wamid (wamid)`` index is intentionally left in place: dropping an index
on the partitioned 10M+ ledger is a heavier, riskier operation than this milestone warrants, and
the repository's additive-only discipline (``REPOSITORY_RULES.md``) prefers leaving it. It becomes
a cleanup candidate once no unscoped provider-message-id read path remains anywhere.

Revision ID: 0042_scope_provider_message_identity
Revises: 0041_channel_sync_control_plane
"""

from __future__ import annotations

from alembic import op

revision = "0042_scope_provider_message_identity"
down_revision = "0041_channel_sync_control_plane"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_msg_endpoint_wamid"
_TABLE = "messages"
_COLUMNS = ("phone_number_id", "wamid")


def upgrade() -> None:
    op.create_index(_INDEX_NAME, _TABLE, list(_COLUMNS), unique=False)


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name=_TABLE)
