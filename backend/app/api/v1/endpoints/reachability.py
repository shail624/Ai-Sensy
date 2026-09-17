"""WhatsApp reachability (scope §13 — Scan).

Answers "which of our customers can WhatsApp actually reach" from delivery evidence the platform
already holds, without sending anything and without a provider that promises a direct lookup. Meta's
Cloud API has no such lookup, and the tools that claim one drive WhatsApp Web underneath, which
section 13 excludes outright.

Reads require ``contacts:read`` and ``campaigns:read`` together: the rows are contacts, but the
verdict on each is derived entirely from campaign delivery outcomes, and a reader who may not see
campaign results should not be handed a summary of them a contact at a time.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, encode_cursor
from app.models.user import User
from app.repositories.reachability import VERDICTS, ReachabilityRepository
from app.schemas.reachability import (
    ReachabilityCounts,
    ReachabilityPage,
    ReachabilityResponse,
    Verdict,
)

router = APIRouter()

ScanReader = Annotated[User, Depends(require_permissions("contacts:read", "campaigns:read"))]


@router.get(
    "/scan/reachability",
    response_model=ReachabilityPage,
    summary="Which contacts WhatsApp has reached, refused, or never been asked about",
)
async def list_reachability(
    session: SessionDep,
    actor: ScanReader,
    verdict: Annotated[
        Verdict | None, Query(description=f"Filter to one verdict: {', '.join(VERDICTS)}.")
    ] = None,
    q: Annotated[str | None, Query(description="Match a contact's name or number.")] = None,
    limit_param: Annotated[
        int | None, Query(alias="limit", ge=1, le=MAX_LIMIT, description="Page size (default 50).")
    ] = None,
    cursor_param: Annotated[
        str | None, Query(alias="cursor", description="Opaque token from a prior next_cursor.")
    ] = None,
) -> ReachabilityPage:
    """Every contact, with what WhatsApp has told us about their number.

    A delivery receipt proves the number is reachable; error 131026 is Meta calling it not a
    WhatsApp user. Nothing else counts — a paused template or a closed 24-hour window is a fact
    about our configuration, not about the customer, and treating those as "not on WhatsApp" would
    condemn reachable people for our own mistakes.

    `unknown` is a real answer: a contact no campaign has ever included has not been tested. It is
    reported as untested rather than folded into either side, because the difference between "we
    know they are not there" and "we have never asked" changes what an operator does next.

    The tallies live at `/scan/reachability/counts`, not here. They are computed from the same
    predicates as this page, so the two can never describe different sets, but they cost what
    reading every recipient row costs and a page should not wait behind them.
    """
    repo = ReachabilityRepository(session)
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    rows, has_more = await repo.paginate(
        actor.organization_id,
        limit=limit,
        cursor=decode_cursor(cursor_param) if cursor_param else None,
        verdict=verdict,
        q=q,
    )
    next_cursor = (
        encode_cursor(rows[-1].contact.created_at, rows[-1].contact.id)
        if has_more and rows
        else None
    )
    return ReachabilityPage(
        data=[ReachabilityResponse.from_row(row) for row in rows],
        page=Page(limit=limit, has_more=has_more, next_cursor=next_cursor),
    )


@router.get(
    "/scan/reachability/counts",
    response_model=ReachabilityCounts,
    summary="How many contacts are in each reachability state",
)
async def reachability_counts(
    session: SessionDep,
    actor: ScanReader,
    q: Annotated[str | None, Query(description="Match a contact's name or number.")] = None,
) -> ReachabilityCounts:
    """The tallies, separately from the rows, because they cost differently.

    A page is fifty contacts and costs what fifty contacts cost. "How many are in each state" is a
    question about every contact the organization has, and no index makes that cheaper — every
    recipient row must be read to decide one contact's verdict. Measured at 200,000 recipients: the
    page takes 9ms and the tallies 425ms.

    Returned together, the fast answer waited for the slow one and the whole screen took half a
    second. Split, the list appears immediately and the tallies fill in. Same numbers, same
    predicates as the list — they cannot describe different sets — and nothing is approximated to
    make it quicker.
    """
    counts = await ReachabilityRepository(session).counts(actor.organization_id, q=q)
    return ReachabilityCounts(**counts)
