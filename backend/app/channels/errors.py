"""Channel-neutral errors (Doc 07 §5.3, Doc 06 §6).

Callers catch **these**, never a provider's exception type — that is part of what keeps channel
knowledge behind the seam. Concrete adapters subclass them (e.g. ``MetaApiError``) and register an
error map with the retry engine, which is what turns an error into a
:class:`~app.queue.retry.FailureClass` (Doc 06 §6.6, decision D12).

Deliberately plain exceptions, not :class:`~app.core.exceptions.AppError`: an adapter fault is not
an HTTP problem. The module that owns the API decides how (and whether) a channel failure surfaces
to a client — Doc 04 §14 maps most of them to ``502``.
"""

from __future__ import annotations


class ChannelError(RuntimeError):
    """Base for every failure raised across the channel seam."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(message)


class ChannelConfigError(ChannelError):
    """The adapter is not usable as configured (missing token, unknown connector).

    Distinct from an auth *rejection*: this one never reaches the network.
    """


class ChannelAuthError(ChannelError):
    """The channel rejected our credentials (expired/revoked token, insufficient scope)."""


class ChannelNotSupported(ChannelError):
    """The adapter does not declare the capability required for this operation (Doc 07 §5.2)."""


class ChannelTransportError(ChannelError):
    """The channel could not be reached (timeout, connection reset, DNS).

    Network-shaped, so the retry engine treats it as transient (Doc 06 §6.2).
    """


class ChannelApiError(ChannelError):
    """The channel was reached and returned an error.

    ``code``/``http_status`` are what a registered error map classifies on (Doc 06 §6.2).
    """

    def __init__(
        self,
        message: str,
        *,
        code: int | str | None = None,
        http_status: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        super().__init__(message, detail=detail)
