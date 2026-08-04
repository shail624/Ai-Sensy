from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
stamp = "2026-08-04T15:24:00+05:30"


def replace_once(path_name: str, old: str, new: str) -> None:
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(f"governance marker changed in {path_name}: {old!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def insert_after(path_name: str, marker: str, block: str) -> None:
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if source.count(marker) != 1:
        raise SystemExit(f"governance marker changed in {path_name}: {marker!r}")
    path.write_text(source.replace(marker, marker + block, 1), encoding="utf-8")


insert_after(
    "CHANGELOG.md",
    "## [Unreleased]\n",
    "\n### 2026-08-04 — Customer Identity Resolution (M13-02)\n\n"
    "**Added**\n"
    "- Added exact tenant-scoped provider and endpoint identities linked to the canonical Contact, "
    "with immutable ownership, factual confidence, ambiguous/conflict detection and a restricted "
    "manual-review queue.\n"
    "- Added non-destructive merge recommendations with explicit approve/reject decisions, RBAC, "
    "feature flags, Audit and Customer Timeline evidence.\n"
    "- Added migration `0036_customer_identity_resolution`, seven additive API paths, generated "
    "OpenAPI/client authority and focused identity regressions.\n\n"
    "**Preserved**\n"
    "- M13-01 channel foundations, canonical Contact ownership and existing CRM, Inbox, Customer 360, "
    "Timeline and Audit authorities remain unchanged; approval never merges Contacts or moves identities.\n"
    "- No M13-03 session/connection control-plane, provider runtime, QR pairing, messaging, UI route or "
    "provider selection work is included.\n\n"
    "**Validated**\n"
    "- Ruff, strict mypy across 271 source files, 22 focused tests and all 961 backend tests pass.\n"
    "- Frontend production audit, ESLint, TypeScript, Vitest and production build pass; OpenAPI has "
    "200 paths and the generated client is current.\n"
    "- Migration upgrade/downgrade/upgrade passes. M13-02 reaches `Repository Validated`; host/runtime "
    "commissioning remains pending.\n",
)

replace_once(
    "IMPLEMENTATION_TRACKER.md",
    "_Last updated: 2026-08-04 · M13-01 Generic Channel Foundation is Repository Validated. No\n"
    "provider, persisted channel connection or executable omnichannel workflow has started._",
    "_Last updated: 2026-08-04 · M13-02 Customer Identity Resolution is Repository Validated. "
    "M13-03 has not started._",
)
replace_once(
    "IMPLEMENTATION_TRACKER.md",
    "- **Migration/OpenAPI:** `0035_notification_center` · 193 paths · unchanged\n"
    "- **Current milestone:** `M13-01 — Generic Channel Foundation — REPOSITORY VALIDATED`\n"
    "- **Module 13 completion:** `8%` evidence-based foundation estimate\n"
    "- **Provider selection:** pending; no provider is registered\n"
    "- **Next milestone:** `M13-02` — not authorized\n"
    "- **Last synchronized:** `2026-08-04T12:56:16+05:30`",
    "- **Migration/OpenAPI:** `0036_customer_identity_resolution` · 200 paths\n"
    "- **Current milestone:** `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED`\n"
    "- **Module 13 completion:** `16%` evidence-based estimate\n"
    "- **Provider selection:** pending; no provider is registered\n"
    "- **Next milestone:** `M13-03` — not started\n"
    f"- **Last synchronized:** `{stamp}`",
)
insert_after(
    "IMPLEMENTATION_TRACKER.md",
    "## Delivered\n",
    "\n### M13-02 Customer Identity Resolution\n\n"
    "- Canonical Contact-based exact identity resolution with immutable provider/endpoint aliases.\n"
    "- Tenant-scoped conflict/review queue and non-destructive recommendations with explicit decisions.\n"
    "- RBAC, disabled-by-default feature flag, Audit/Timeline integration, migration `0036`, "
    "200-path OpenAPI and generated TypeScript authority.\n"
    "- Repository gates: Ruff PASS, mypy PASS (271 files), 22 focused and 961 full backend tests PASS; "
    "frontend lint/type/Vitest/build and migration/client generation PASS.\n\n",
)
replace_once(
    "IMPLEMENTATION_TRACKER.md",
    "- M13-02 identity convergence is not authorized.\n",
    "- M13-03 session and connection control plane is not started.\n",
)
replace_once(
    "IMPLEMENTATION_TRACKER.md",
    "Do not begin M13-02 or any unassigned persistence/provider work.",
    "Do not begin M13-03 or any unassigned persistence/provider work.",
)

replace_once(
    "PROJECT_STATE.md",
    "| Current Git HEAD | `HEAD` (M13-01 closeout; resolve after push) |\n"
    "| Current milestone | `M13-01 — Generic Channel Foundation — REPOSITORY VALIDATED` |\n"
    "| Current phase | `Provider-neutral omnichannel contracts delivered; no provider/runtime/persistence workflow started` |",
    "| Current Git HEAD | `HEAD` (M13-02 closeout; resolve after push) |\n"
    "| Current milestone | `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED` |\n"
    "| Current phase | `Exact Contact identity convergence and restricted manual review delivered; M13-03 unstarted` |",
)
replace_once(
    "PROJECT_STATE.md",
    "| Migration head | `0035_notification_center` (35 linear revisions; unchanged) |\n"
    "| OpenAPI | `3.1.0` · `193` paths · generated TypeScript authority unchanged |\n"
    "| Backend evidence | Ruff PASS · strict mypy PASS across 263 source files · 46 focused tests PASS · 955 full pytest tests PASS |",
    "| Migration head | `0036_customer_identity_resolution` (36 linear revisions) |\n"
    "| OpenAPI | `3.1.0` · `200` paths · generated TypeScript authority current |\n"
    "| Backend evidence | Ruff PASS · strict mypy PASS across 271 source files · 22 focused tests PASS · 961 full pytest tests PASS |",
)
replace_once(
    "PROJECT_STATE.md",
    "| Module 13 implementation | `8%` evidence-based estimate: provider-neutral in-process foundation only; no channel connection persistence or provider behavior |\n"
    "| QR provider | Not selected; Required evaluation remains external |\n"
    "| Next Module 13 milestone | `M13-02`; not authorized and not started |",
    "| Module 13 implementation | `16%` evidence-based estimate: generic foundation plus exact Customer identity convergence |\n"
    "| QR provider | Not selected; Required evaluation remains external |\n"
    "| Next Module 13 milestone | `M13-03`; not started |",
)
replace_once(
    "PROJECT_STATE.md",
    "| Last update | `2026-08-04T12:56:16+05:30` (Asia/Kolkata) |",
    f"| Last update | `{stamp}` (Asia/Kolkata) |",
)
insert_after(
    "PROJECT_STATE.md",
    "## M13-01 delivered foundation\n",
    "\n## M13-02 delivered identity resolution\n\n"
    "- Added exact organization/namespace/scope/value identity normalization and immutable Contact ownership.\n"
    "- Added ambiguity/conflict detection, tenant-scoped review queue and non-destructive merge recommendations.\n"
    "- Added explicit approve/reject decisions with row-version checks, RBAC, feature flag, Audit and Timeline evidence.\n"
    "- Added migration `0036_customer_identity_resolution`, seven API paths and regenerated OpenAPI/client authority.\n"
    "- No Contact merge is executed and no identity ownership is moved by this milestone.\n\n",
)
replace_once(
    "PROJECT_STATE.md",
    "Stop after M13-01. Do not begin M13-02, persistence/backfill work, provider selection or any\nprovider/runtime implementation without a separate explicit owner instruction.",
    "Stop after M13-02. Do not begin M13-03, persistence/backfill work, provider selection or any\nprovider/runtime implementation without a separate explicit owner instruction.",
)

replace_once(
    "MODULE_STATUS.md",
    "Last synchronized: `2026-08-04T12:56:16+05:30`.",
    f"Last synchronized: `{stamp}`.",
)
insert_after(
    "MODULE_STATUS.md",
    "## Module 13 — M13-01 generic channel foundation\n",
    "\n## Module 13 — M13-02 customer identity resolution\n\n"
    "- **Milestone status:** `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED`.\n"
    "- **Completion:** `16%` evidence-based estimate.\n"
    "- **Delivered:** canonical Contact identity aliases, exact scoped resolution, confidence, conflict detection, "
    "tenant review queue, recommendations, approve/reject, RBAC, feature flag, Audit/Timeline, migration/API/client.\n"
    "- **Preserved:** no automatic/destructive Contact merge, provider runtime, QR workflow or M13-03 work.\n"
    "- **Next:** M13-03 is not started. Host/provider/runtime commissioning remains pending.\n\n",
)
replace_once(
    "MODULE_STATUS.md",
    "| Enterprise Omnichannel Channel Manager | 8% | M13-00 contract plus M13-01 provider-neutral intent/policy/metadata/health/lifecycle contracts, registries, validation, flags and DI are Repository Validated; existing ChannelAdapter is reused | Persistent connection/endpoint/secret records and Meta backfill remain Required; no provider/runtime/API/UI exists; M13-02 not authorized | Existing ChannelAdapter/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020 and Design Document 33 |",
    "| Enterprise Omnichannel Channel Manager | 16% | M13-00/M13-01 plus M13-02 exact Contact identity convergence, immutable aliases, conflict review, recommendations, RBAC, Audit/Timeline, migration `0036` and 200-path API are Repository Validated | Persistent connection/endpoint/secret records and Meta backfill remain Required; provider/runtime/UI absent; M13-03 not started | Existing Contact/ChannelAdapter/capabilities, FeatureFlag, RBAC/tenant/audit foundations, frozen ADR-0020 and Design Document 33 |",
)
replace_once(
    "MODULE_STATUS.md",
    "| API | 85% | 193-path OpenAPI 3.1 contract; CORE-09 adds four notification paths while preserving generated TypeScript authority |",
    "| API | 87% | 200-path OpenAPI 3.1 contract; M13-02 adds seven identity-resolution/review paths with generated TypeScript authority |",
)

replace_once(
    "ROADMAP.md",
    "Last synchronized: `2026-08-04T12:56:16+05:30`.",
    f"Last synchronized: `{stamp}`.",
)
replace_once(
    "ROADMAP.md",
    "**Current status: M13-01 — Generic Channel Foundation — REPOSITORY VALIDATED**",
    "**Current status: M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED**",
)
replace_once(
    "ROADMAP.md",
    "| M13-02 — Customer identity convergence | Add exact scoped provider identities and conflict handling without duplicate Contacts | Not authorized; blocked by explicit owner instruction and required foundation gates |\n"
    "| M13-03 — Session and connection control plane | Durable session state, lease/fencing and runtime foundation | Blocked by provider approval, persistence and M13-02 |",
    "| M13-02 — Customer identity convergence | Add exact scoped provider identities and conflict handling without duplicate Contacts | **REPOSITORY VALIDATED**; immutable aliases, review queue and non-destructive recommendations delivered |\n"
    "| M13-03 — Session and connection control plane | Durable session state, lease/fencing and runtime foundation | Not started; blocked by provider approval and persistence |",
)
replace_once(
    "ROADMAP.md",
    "Stop after M13-01. No M13-02, persistence/backfill, provider selection or runtime work begins\nautomatically.",
    "Stop after M13-02. No M13-03, persistence/backfill, provider selection or runtime work begins\nautomatically.",
)

replace_once(
    "VALIDATION_RESULTS.md",
    "Last synchronized: `2026-08-04T12:56:16+05:30`.",
    f"Last synchronized: `{stamp}`.",
)
insert_after(
    "VALIDATION_RESULTS.md",
    f"Last synchronized: `{stamp}`.\n",
    "\n## M13-02 Customer Identity Resolution\n\n"
    "| Validation item | Status | Latest evidence |\n"
    "|---|---|---|\n"
    "| Latest Git baseline | PASS | Work starts from `c238bfa55d050310f865771be4654b90a5a993d2` on `ui/taste-modernization`. |\n"
    "| Exact canonical identity | PASS | Organization/namespace/scope/value keys resolve only to the canonical Contact; fuzzy/profile-name matching is absent. |\n"
    "| Immutable aliases and endpoint identities | PASS | Unique tenant-scoped ownership, provider/endpoint metadata and immutable links are enforced. |\n"
    "| Ambiguity/conflict handling | PASS | Multiple/no authoritative candidates create a tenant-scoped review item; no automatic merge or ownership move occurs. |\n"
    "| Recommendation decisions | PASS | Pending recommendations support explicit approve/reject with optimistic concurrency and never execute a merge. |\n"
    "| RBAC, tenant and feature flag | PASS | Contact permissions, organization predicates and disabled-by-default `omnichannel_identity_resolution` fail closed. |\n"
    "| Audit and Timeline | PASS | Link, conflict, recommendation and decision facts use existing Audit and Contact Timeline authorities. |\n"
    "| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 271 source files. |\n"
    "| Backend tests | PASS | 22 focused identity/contact/channel tests and all 961 backend tests pass. |\n"
    "| Frontend gates | PASS | Production audit, ESLint, TypeScript, Vitest and production build pass; application source is unchanged. |\n"
    "| OpenAPI / generated client | PASS | OpenAPI 3.1 has 200 paths and generated TypeScript authority is current. |\n"
    "| Migration | PASS | `0036_customer_identity_resolution` upgrades, downgrades to `0035`, and upgrades again with all three tables present. |\n"
    "| Bundle impact | PASS | Generated contract only; CSS, main and lazy-route application bundles remain unchanged and the existing >500 kB warning remains. |\n"
    "| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration, representative operator review, production feature-flag rollout and runtime/security commissioning remain unproven. |\n"
    "| Milestone boundary | PASS | M13-01 is unchanged and M13-03/provider/runtime/QR/UI work is absent. |\n",
)
