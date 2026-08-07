"""Channel abstraction (Doc 07 §5) — the single seam to every messaging channel.

The whole platform talks to channels **only** through :class:`~app.channels.base.ChannelAdapter`.
Nothing channel-specific crosses the seam: adapters translate native payloads to and from the
canonical objects in :mod:`app.channels.models`, so the CRM, queue, API, UI and analytics never
learn that Meta (or any future channel) exists (Doc 07 §5.1/§5.3, decision CD1).

Adapters are **capability-based**: each declares what it can do and the platform checks the flag
rather than branching on channel identity (§5.2). Adding a channel is a new adapter registered
into the registry — the engine is untouched (§5.4).

Importing a concrete adapter package registers it, mirroring the storage provider pattern::

    import app.channels.meta  # registers the 'meta_cloud' adapter + its error map
    import app.channels.waha  # registers the 'waha' QR adapter (inert, disabled by default)

Registration makes an adapter *resolvable*, never *enabled*: it opens no socket, needs no
credential, and starts no runtime. A provider without configuration simply raises
:class:`~app.channels.errors.ChannelConfigError` if something asks it to reach its server.

``waha`` is registered here explicitly so every process (API, workers, beat, CLI) resolves it
deterministically rather than as a side effect of whichever service module happened to be imported
first. It is safe to do at package-import time precisely because registration is inert. ``meta`` is
deliberately left on its existing import path so Meta's behaviour is unchanged by this milestone.
"""

from __future__ import annotations

from app.channels import waha as waha  # noqa: F401 — registers the inert 'waha' adapter factory
