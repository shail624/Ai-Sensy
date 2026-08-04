from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path.cwd()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected text not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_fixes() -> None:
    pairing = ROOT / "backend/app/services/pairing_manager.py"
    text = pairing.read_text(encoding="utf-8")
    wrong_imports = (
        "    PairingState,\n"
        "    RuntimeMetadata,\n"
        "    RuntimeEvent,\n"
        "    RuntimeEventType,\n"
    )
    correct_imports = (
        "    PairingState,\n"
        "    RuntimeEvent,\n"
        "    RuntimeEventType,\n"
        "    RuntimeMetadata,\n"
    )
    if wrong_imports in text:
        text = text.replace(wrong_imports, correct_imports, 1)
    elif correct_imports not in text:
        raise SystemExit("pairing import block not found")

    old_method = '''    async def expire_due_pairings(
        self,
        *,
        organization_id: int,
        actor: User,
        at: datetime | None = None,
    ) -> list[ChannelSession]:
        """Expire due pairing availability without requiring a now-dead runtime lease."""

        await self._require_authenticate(organization_id, actor)
        now = at or utcnow()
        rows = await self._sessions.list_due_pairings(organization_id, now)
'''
    new_method = '''    async def expire_due_pairings(
        self,
        *,
        organization_id: int,
        actor: User,
        at: datetime | None = None,
        limit: int = 100,
    ) -> list[ChannelSession]:
        """Expire due pairing availability without requiring a now-dead runtime lease."""

        await self._require_authenticate(organization_id, actor)
        if limit < 1 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000.")
        now = at or utcnow()
        rows = await self._sessions.list_due_pairings(organization_id, now, limit=limit)
'''
    if old_method in text:
        text = text.replace(old_method, new_method, 1)
    elif new_method not in text:
        raise SystemExit("expire_due_pairings block not found")
    pairing.write_text(text, encoding="utf-8")

    repository = ROOT / "backend/app/repositories/channel_session.py"
    text = repository.read_text(encoding="utf-8")
    old_repo = '''    async def list_due_pairings(
        self, organization_id: int, at: datetime
    ) -> list[ChannelSession]:
'''
    new_repo = '''    async def list_due_pairings(
        self, organization_id: int, at: datetime, *, limit: int = 100
    ) -> list[ChannelSession]:
'''
    if old_repo in text:
        text = text.replace(old_repo, new_repo, 1)
    elif new_repo not in text:
        raise SystemExit("list_due_pairings signature not found")
    old_order = '''            .order_by(ChannelSession.pairing_expires_at.asc(), ChannelSession.id.asc())
            .with_for_update()
'''
    new_order = '''            .order_by(ChannelSession.pairing_expires_at.asc(), ChannelSession.id.asc())
            .limit(limit)
            .with_for_update()
'''
    if old_order in text:
        text = text.replace(old_order, new_order, 1)
    elif new_order not in text:
        raise SystemExit("list_due_pairings query not found")
    repository.write_text(text, encoding="utf-8")

    tests = ROOT / "backend/tests/test_provider_runtime.py"
    text = tests.read_text(encoding="utf-8")
    invalid_limit = '''    with pytest.raises(ValidationError, match="limit"):
        await pairing.expire_due_pairings(
            organization_id=organization.id,
            actor=actor,
            at=now + timedelta(seconds=21),
            limit=0,
        )

'''
    anchor = '''    expired = await pairing.expire_due_pairings(
        organization_id=organization.id,
        actor=actor,
        at=now + timedelta(seconds=21),
    )
'''
    if invalid_limit not in text:
        if anchor not in text:
            raise SystemExit("pairing expiry test anchor not found")
        text = text.replace(anchor, invalid_limit + anchor, 1)
    tests.write_text(text, encoding="utf-8")


def update_governance() -> None:
    backend_tests = os.environ["BACKEND_TESTS"]
    focused_tests = os.environ["FOCUSED_TESTS"]
    run_id = os.environ["VALIDATION_RUN_ID"]
    timestamp = os.environ.get("M13_TIMESTAMP", "2026-08-04T22:45:00+05:30")

    project_state = f'''# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `HEAD` (M13-05 closeout; resolve after push) |
| Current milestone | `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED` |
| Current phase | `Provider-neutral runtime registration, pairing state and runtime/session integration delivered; M13-06 unstarted` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0039_qr_pairing_provider_runtime_foundation` (39 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · no public runtime/pairing route or generated TypeScript change |
| Backend evidence | Ruff PASS · strict mypy PASS · {focused_tests} focused channel/session/runtime/migration tests PASS · {backend_tests} full pytest tests PASS |
| Frontend evidence | Unchanged source; production audit high threshold PASS · ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Bundle evidence | Unchanged: main `733.62 kB` / `178.16 kB` gzip; CSS `49.90 kB` / `9.90 kB` gzip; Operational Dashboard `31.96 kB` / `8.61 kB` gzip; existing >500 kB warning remains |
| M13 contract | ADR-0020 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `40%` evidence-based estimate: generic contracts, exact identity, persistent connections, session control plane, provider-neutral runtime registry and no-store pairing lifecycle |
| QR provider | Not selected; no provider adapter, QR image, WhatsApp protocol or live provider login exists |
| Next Module 13 milestone | `M13-06`; not started |
| Host evidence | Target-host MySQL migration, real multi-node runtime/lease contention, provider certification, runtime supervision/monitoring, KMS custody and staged tenant/RBAC/flag commissioning remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | Sixteen runtime/session/model/repository/service/permission/migration/test files plus six required governance records; no API, generated contract, frontend, provider adapter, messaging, synchronization or M13-06 change |
| Last update | `{timestamp}` (Asia/Kolkata) |

## M13-05 delivered provider runtime and pairing foundation

- Added provider-neutral runtime metadata, lifecycle, event and health contracts plus a thread-safe runtime registry that resolves executable behavior only through the existing `ChannelAdapter` seam.
- Added `ProviderRuntimeManager` registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat integration, restart/recovery metadata and durable `ChannelSession` projection.
- Added a no-store `PairingManager` abstraction with governed `UNPAIRED`, `PAIRING_REQUESTED`, `PAIRING_AVAILABLE`, `PAIRING_EXPIRED`, `PAIRING_CANCELLED`, `PAIRED` and `ACTIVE` transitions; no QR payload, image, token or provider credential is persisted.
- Reused M13-04 lease/fencing, optimistic concurrency, session ownership, health, heartbeat, restart/recovery and Audit authorities rather than creating a second runtime truth table.
- Added disabled-by-default runtime/pairing flags, runtime/pairing RBAC permissions, additive migration `0039_qr_pairing_provider_runtime_foundation` and tenant-scoped expiry sweeps bounded to 1–1000 records.

## Preserved completed foundations

- M13-01 provider metadata/capability registries, M13-02 Contact identity, M13-03 connection/endpoint/encrypted-secret persistence and M13-04 session lifecycle/lease/fencing remain authoritative.
- Existing Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, message, media and Audit authorities remain unchanged.

## Preserved boundaries

- No QR image generation/scanning, WhatsApp login or protocol, provider adapter, history/message synchronization, incoming/outgoing messages, webhook runtime, routing, Inbox, Customer 360, Analytics or frontend behavior exists.
- No public API route, OpenAPI path, generated client surface, provider dependency, provider-specific table or runtime message storage was added.
- Pairing persistence contains state, timestamps and constrained reason codes only; secret references continue to use existing encrypted credential records.

## Validation boundary

Repository validation proves provider-neutral registry/runtime/pairing contracts, tenant/RBAC/flag
boundaries, durable session integration, lease/fencing enforcement, bounded expiry, health, heartbeat,
restart/recovery metadata, Audit redaction, additive migration, lint, typing, full regressions, source
security scans and unchanged frontend/API semantics. OpenAPI generation under the current unpinned
FastAPI/Pydantic resolver has a pre-existing JSON key-order mismatch at the untouched M13-04 baseline;
semantic schemas are equal and M13-05 introduces no route or schema. It does not prove a live provider,
QR scan/login, target-host multi-node runtime behavior, provider certification, production monitoring,
disaster recovery or rollout.

## Required remaining contract work

Target-host commissioning, provider selection/certification, live inbound/history/media, outbound
messaging and unified operator experience remain later gated milestones. M13-06 is not started.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated host review pending.
M13-05 changes no frontend source or UI modernization sequence.

## Maintenance rule

Stop after M13-05. Do not begin M13-06, provider selection/backfill, QR image/login, provider adapters,
messaging, synchronization, webhook, routing or UI work without a separate explicit owner instruction.
'''
    (ROOT / "PROJECT_STATE.md").write_text(project_state, encoding="utf-8")

    tracker = f'''# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-04 · M13-05 QR Pairing & Provider Runtime Foundation is Repository Validated. M13-06 has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `5d7ea154588418410611de4f568e978c2e3caba9`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0039_qr_pairing_provider_runtime_foundation` · 200 paths
- **Current milestone:** `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED`
- **Module 13 completion:** `40%` evidence-based estimate
- **Provider selection:** pending; no provider adapter or live provider is registered
- **Next milestone:** `M13-06` — not started
- **Last synchronized:** `{timestamp}`

## Delivered

### M13-05 QR Pairing & Provider Runtime Foundation

- Provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing adapter seam.
- Tenant-scoped runtime registration, discovery and ownership; durable capability observations, health/lifecycle reports, heartbeat, restart policy and recovery metadata on the existing `ChannelSession` authority.
- No-store pairing lifecycle with constrained state/reason/timestamp facts only; no QR payload, image, token, protocol credential or login implementation.
- Lease/fencing and optimistic-concurrency enforcement for runtime reports; holder-specific observations reset safely when runtime ownership changes.
- Disabled-by-default runtime/pairing flags, dedicated permissions, Audit coverage and bounded pairing-expiry processing.
- Additive migration `0039_qr_pairing_provider_runtime_foundation`; no API, generated-contract or frontend source change.

### Preserved M13-01 through M13-04 authorities

- Existing `ChannelAdapter`, provider metadata/capability registries, canonical Contact identity, persistent connection/endpoint/encrypted-secret records and durable session lifecycle/lease/fencing remain authoritative.
- No provider implementation, duplicate persistence authority or shared CRM/message/UI authority was added.

## Validation

- Ruff PASS.
- Strict mypy PASS.
- Focused channel/session/runtime/migration suite: {focused_tests} PASS.
- Full backend suite: {backend_tests} PASS in workflow `{run_id}`.
- Migration validation PASS at `0039_qr_pairing_provider_runtime_foundation`.
- OpenAPI semantic equality PASS with 200 paths and no M13-05 route/schema/client change; the untouched baseline retains a pre-existing key-order-only exporter mismatch under the current dependency resolver.
- Generated TypeScript client PASS with no drift.
- Python dependency audit, Bandit high-severity and tracked-source vulnerability/secret/IaC scan PASS.
- Frontend production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build PASS with unchanged source.
- Bundle output remains unchanged: CSS 49.90/9.90 kB gzip, main 733.62/178.16 kB gzip and Operational Dashboard 31.96/8.61 kB gzip.
- Exact sixteen-file implementation boundary PASS before governance; no API, frontend, provider adapter, messaging, synchronization or M13-06 file changed.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, message/history
synchronization, sending, incoming webhooks, routing, Inbox/Customer 360/Analytics changes, public
runtime/pairing APIs and provider-specific tables are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider selection/certification and all M13-06+ inbound/history/media/messaging/operator milestones.

## Stop rule

Do not begin M13-06 or any live QR image/login, provider adapter, messaging, synchronization, webhook,
routing, Inbox, Customer 360 or Analytics work. Any architecture or scope deviation requires owner approval.
'''
    (ROOT / "IMPLEMENTATION_TRACKER.md").write_text(tracker, encoding="utf-8")

    module = ROOT / "MODULE_STATUS.md"
    text = module.read_text(encoding="utf-8")
    text = text.replace(
        "Last synchronized: `2026-08-04T19:05:00+05:30`.",
        f"Last synchronized: `{timestamp}`.",
        1,
    )
    marker = "## Module 13 — M13-04 QR Session Manager Foundation\n"
    block = f'''## Module 13 — M13-05 QR Pairing & Provider Runtime Foundation

- **Milestone status:** `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED`.
- **Completion:** `40%` evidence-based estimate.
- **Delivered:** provider-neutral runtime contracts/registry, runtime registration/discovery/ownership, health/lifecycle/events, capability publication, heartbeat/restart/recovery integration and no-store pairing lifecycle persisted on the existing session authority.
- **Security:** tenant/RBAC/flags fail closed; stale holders require valid fencing; pairing stores no QR/token/credential payload; reason codes are constrained and every transition is audited.
- **Preserved:** no QR image/scanning/login, WhatsApp protocol, provider adapter, synchronization, messaging, webhook, routing, Inbox/Customer 360/Analytics, API path or frontend change.
- **Next:** M13-06 is not started. Host MySQL, multi-node runtime, provider certification, supervisor/monitoring, KMS and rollout commissioning remain pending.

'''
    if marker not in text:
        raise SystemExit("MODULE_STATUS M13-04 marker missing")
    text = text.replace(marker, block + marker, 1)
    old_row = "| Enterprise Omnichannel Channel Manager | 32% | M13-00–M13-04 are Repository Validated: provider-neutral contracts, exact Contact identity, persistent connection/endpoint/encrypted-secret records and durable session lifecycle/lease/fencing foundation; migrations `0036`–`0038`; unchanged 200-path API | Target-host MySQL/KMS and multi-node session commissioning, provider selection/adapters, QR pairing, messaging and UI remain pending; M13-05 not started | Existing Contact/Organization/ChannelConnection/ChannelAdapter/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020 and Design Document 33 |"
    new_row = "| Enterprise Omnichannel Channel Manager | 40% | M13-00–M13-05 are Repository Validated: provider-neutral contracts, exact Contact identity, persistent connections/secrets, durable session lease/fencing and runtime/pairing control-plane foundation; migrations `0036`–`0039`; unchanged 200-path API | Target-host MySQL/KMS, multi-node runtime commissioning, provider selection/adapters, live QR/login, inbound/history/media, messaging and UI remain pending; M13-06 not started | Existing Contact/Organization/ChannelConnection/ChannelSession/ChannelAdapter/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020 and Design Document 33 |"
    if old_row not in text:
        raise SystemExit("MODULE_STATUS module row missing")
    module.write_text(text.replace(old_row, new_row, 1), encoding="utf-8")

    validation = ROOT / "VALIDATION_RESULTS.md"
    text = validation.read_text(encoding="utf-8")
    text = text.replace(
        "Last synchronized: `2026-08-04T19:05:00+05:30`.",
        f"Last synchronized: `{timestamp}`.",
        1,
    )
    insert = f'''## M13-05 QR Pairing & Provider Runtime Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5d7ea154588418410611de4f568e978c2e3caba9` on `ui/taste-modernization`. |
| Provider-neutral runtime abstraction | PASS | Runtime metadata, lifecycle, events, health and pairing contracts contain no provider-specific branch and resolve execution only through the existing adapter seam. |
| Runtime registration/discovery/ownership | PASS | Thread-safe registry and tenant-scoped manager reject duplicate/conflicting runtime registrations, foreign organizations and unauthorized actors. |
| Session and persistence reuse | PASS | Runtime/pairing facts extend existing `ChannelSession` and `ChannelConnection`; no duplicate runtime, connection, credential, message or history authority exists. |
| Pairing lifecycle | PASS | UNPAIRED → PAIRING_REQUESTED → PAIRING_AVAILABLE with governed expiry/cancel/pair/active paths rejects illegal transitions and accepts no QR payload or token. |
| Runtime lifecycle/events/health | PASS | Factual lifecycle, event, health and capability observations persist with timezone-aware evidence and no live-provider claim. |
| Heartbeat, restart and recovery | PASS | Existing session heartbeat, lease/fencing, restart policy and recovery metadata are reused; stale holders and invalid fencing tokens fail closed. |
| Pairing expiry safety | PASS | Availability cannot be accepted after expiry, provider TTL is bounded, and expiry sweeps validate and limit batches to 1–1000 locked rows. |
| Security boundary | PASS | Tenant isolation, RBAC, disabled-by-default flags, constrained reason codes, secret-reference-only storage and Audit redaction are enforced. |
| Audit coverage | PASS | Runtime registration/ownership/lifecycle/health/capability/heartbeat/recovery and every pairing transition emit safe existing Audit evidence. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | {focused_tests} focused channel/session/runtime/migration tests and all {backend_tests} backend tests pass in workflow `{run_id}`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | Application and committed OpenAPI are semantically identical at 200 paths and generated TypeScript has no drift. Current dependency resolution exposes a pre-existing JSON key-order-only `--check` mismatch on the untouched M13-04 baseline; M13-05 adds no route/schema. |
| Migration | PASS | Additive `0039_qr_pairing_provider_runtime_foundation` upgrades, downgrades to `0038`, and upgrades again without destructive existing-schema changes. |
| Bandit / dependency / source scan | PASS | Bandit high-severity, Python dependency, frontend/browser audit thresholds and tracked-source vulnerability/secret/IaC scan pass. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL, real multi-node runtime/lease contention, provider certification, runtime supervisor/monitoring, KMS custody and representative tenant/RBAC/flag rollout remain unproven. |
| Milestone boundary | PASS | Exact sixteen-file implementation boundary before governance; M13-01–M13-04 remain authoritative and M13-06, provider adapters, QR image/login, sync, messaging, webhooks, routing and UI are absent. |

'''
    marker = "## M13-04 QR Session Manager Foundation\n"
    if marker not in text:
        raise SystemExit("VALIDATION_RESULTS M13-04 marker missing")
    validation.write_text(text.replace(marker, insert + marker, 1), encoding="utf-8")

    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    entry = f'''### 2026-08-04 — QR Pairing & Provider Runtime Foundation (M13-05)

**Added**
- Added provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing `ChannelAdapter` seam.
- Added tenant-scoped runtime registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat, restart/recovery metadata and durable session integration.
- Added a no-store pairing lifecycle with governed request/available/expired/cancelled/paired/active transitions, dedicated feature flags/RBAC/Audit and migration `0039_qr_pairing_provider_runtime_foundation`.

**Security**
- Runtime reports require valid lease fencing, pairing TTL and expiry are enforced, expiry sweeps are bounded, reason codes are constrained, and no QR payload, token, protocol credential or provider secret is stored or audited.

**Preserved**
- M13-01 through M13-04 channel, identity, persistence and session authorities remain intact; no duplicate provider/runtime/connection/message authority was introduced.
- No QR image generation/scanning, WhatsApp login/protocol, provider adapter, message/history synchronization, incoming/outgoing messaging, webhook, routing, Inbox/Customer 360/Analytics, API or frontend work is included.

**Validated**
- Ruff, strict mypy, {focused_tests} focused tests and all {backend_tests} backend tests pass in workflow `{run_id}`.
- Migration round-trip, generated-client invariance, Bandit, dependency audits and tracked-source security scan pass; OpenAPI remains semantically unchanged at 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-05 reaches `Repository Validated`; host/provider/runtime commissioning remains pending.

'''
    marker = "## [Unreleased]\n\n"
    if marker not in text:
        raise SystemExit("CHANGELOG Unreleased marker missing")
    changelog.write_text(text.replace(marker, marker + entry, 1), encoding="utf-8")

    roadmap = ROOT / "ROADMAP.md"
    text = roadmap.read_text(encoding="utf-8")
    text = text.replace(
        "Last synchronized: `2026-08-04T19:05:00+05:30`.",
        f"Last synchronized: `{timestamp}`.",
        1,
    )
    old_status = '''**Current status: M13-04 — QR Session Manager Foundation — REPOSITORY VALIDATED**

ADR-0020 and Design Document 33 remain frozen. M13-01 supplies the provider-neutral contracts,
registries, generic flags and DI; M13-02 supplies exact Contact identity convergence; M13-03 supplies
provider-neutral connection, endpoint and encrypted-secret persistence; M13-04 now supplies durable
provider-neutral session state, lifecycle, ownership, health, heartbeat/expiration, recovery/restart
metadata and database lease/fencing controls. No provider is selected or registered and no live session exists.

Provider-specific backfill and runtime remain outside this milestone. M13-04 adds no QR generation or
login, provider adapter, synchronization, messaging, webhook, routing or operator-UI behavior.
'''
    new_status = '''**Current status: M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED**

ADR-0020 and Design Document 33 remain frozen. M13-01 supplies provider-neutral contracts and
registries; M13-02 exact Contact identity; M13-03 persistent connection/endpoint/encrypted-secret
records; M13-04 durable session lifecycle/lease/fencing; and M13-05 now supplies provider-neutral
runtime registration/discovery/ownership, lifecycle/events/health/capabilities, heartbeat/restart/
recovery integration and a no-store pairing state machine. No provider is selected and no live login exists.

Provider adapters, QR image generation/scanning, WhatsApp protocol, synchronization, messaging,
webhook, routing and operator UI remain outside this milestone.
'''
    if old_status not in text:
        raise SystemExit("ROADMAP current status block missing")
    text = text.replace(old_status, new_status, 1)
    old_m13_05 = "| M13-05 — QR pairing and health | Pairing, devices, reconnect, re-authentication and diagnostics | Not started; blocked by target-host M13-04 commissioning, provider certification and explicit owner instruction |"
    new_m13_05 = "| M13-05 — QR Pairing & Provider Runtime Foundation | Provider-neutral runtime registry/manager, no-store pairing lifecycle, health/events/capabilities, heartbeat/restart/recovery and session persistence integration | **REPOSITORY VALIDATED**; migration `0039`; no provider adapter, QR image/login, messaging, API or UI behavior |"
    if old_m13_05 not in text:
        raise SystemExit("ROADMAP M13-05 row missing")
    text = text.replace(old_m13_05, new_m13_05, 1)
    text = text.replace(
        "Stop after M13-04. No M13-05, provider selection/backfill, QR pairing/login, provider adapters/runtime,\nmessaging, synchronization, webhook, routing or UI work begins automatically.",
        "Stop after M13-05. No M13-06, provider selection/backfill, live QR image/login, provider adapters,\nmessaging, synchronization, webhook, routing or UI work begins automatically.",
        1,
    )
    roadmap.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("apply-fixes", "update-governance"))
    args = parser.parse_args()
    if args.command == "apply-fixes":
        apply_fixes()
    else:
        update_governance()
