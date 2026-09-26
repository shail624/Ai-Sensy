# WAHA Class B Provider Selection Record

- **Repository:** `shail624/Ai-Sensy`
- **Branch baseline:** `ui/taste-modernization` at `cc824e89336a1dc0d3d3c8c9ee2f7c8b0c11d2cc`
- **Record date:** 2026-08-07
- **Evaluator:** Repository engineering (isolated local certification spike)
- **Provider:** WAHA (WhatsApp HTTP API), `devlikeapro/waha`
- **Evaluated version:** **2026.7.2**, tier **CORE**, engine **NOWEB**, `linux/x64`
  (reported by the running container's `GET /api/server/version`)
- **Licence:** Apache-2.0
- **Provider class:** **Class B — Owner-approved Internal Self-hosted Provider** (ADR-0021)
- **Deployment scope:** Internal, self-hosted, single organization. **Not** SaaS, not multi-customer
  hosted, not marketplace-distributed, not resold
- **Selection outcome:** **Selected as the Class B candidate**
- **Certification status:** **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED**
- **Production certification:** **Pending** — not granted by this record
- **M13-06 / QR-01 status:** Remain **blocked** pending the prerequisites in this record

## Relationship to the prior evaluation record

This record is the Design Document 33 §6.4 **selection record**. It succeeds — and does not rewrite
or invalidate — `waha-class-b-evaluation.md` (2026-08-05, baseline `a313eca4`), which correctly
returned *Requires Additional Evidence* because that evaluation had no exact candidate version and no
executed test environment.

That record's resumption checklist is now partially satisfied. Items closed here: **E-005** (exact
version), **E-006** (licence), **E-010** (controlled deployment), **E-011** (partial — every Required
criterion testable without a paired handset), **E-015** (owner risk acceptance, recorded verbatim
below). Items still open: **E-007** (certification account), **E-008**/**E-009** (device and WhatsApp
application evidence), **E-012** (SBOM/provenance), **E-013**, **E-014**.

This record amends no frozen artefact. ADR-0020, ADR-0021 and Design Document 33 are unchanged.

## Owner approval

Recorded verbatim as supplied by the repository owner on 2026-08-07:

> I, as repository owner, approve WAHA as an ADR-0021 Class B internal self-hosted provider for this
> platform.
>
> I understand that WAHA uses an unofficial WhatsApp Web protocol and is not affiliated with or
> officially authorized by WhatsApp.
>
> I explicitly accept the risk that WhatsApp may restrict or permanently ban numbers connected
> through WAHA. Only numbers whose restriction or loss is acceptable to the business will be
> connected.
>
> This approval is limited to internal, single-organization, self-hosted use only. It does not
> authorize SaaS, resale, multi-customer hosting, bulk messaging, campaigns, or template sending
> through the QR provider.
>
> I approve NOWEB as the initial WAHA engine because the certification spike was successfully
> performed against NOWEB.
>
> Architecture Approval: APPROVED
> Security Approval: APPROVED
> Owner Risk Acceptance: APPROVED

ADR-0021 requires Owner Approval, Architecture Approval, Security Approval and explicit Risk
Acceptance. All four are present above and are recorded as granted by the repository owner.

## Engine selection — NOWEB

**NOWEB is selected as the initial engine**, on evidence rather than preference:

- It is the engine the certification spike actually ran (`WHATSAPP_DEFAULT_ENGINE=NOWEB`), so every
  result in this record describes NOWEB and nothing has to be inferred from another engine.
- It is browserless, avoiding a bundled Chromium/Puppeteer runtime and its attack surface, memory
  footprint and patch burden.
- WAHA's documentation warns that event payload shapes may differ between engines, so the adapter
  must be written against exactly one. Pinning the certified engine is the safe reading.

Changing the engine requires a new owner decision and re-execution of this evidence.

## Required-criteria results (Doc 33 §6.1)

Evidence type: **SPIKE** = directly observed in the isolated local run; **DOC** = official
documentation only; **PENDING** = cannot be evidenced without a paired handset.

| Required area | Result | Evidence |
|---|---|---|
| Legal and policy position | **PASS (Class B only)** | Apache-2.0 permits internal commercial use. WAHA states it is *"not affiliated…with WhatsApp"* and that WhatsApp does not permit unofficial clients. **Fails Class A by definition**; qualifies solely under ADR-0021 Class B with the owner risk acceptance above. |
| Stable identity | **PASS (SPIKE)** | Session-scoped identity; `GET /api/sessions/{s}/me`; per-session namespacing observed. |
| Message identity | **PENDING** | Event envelope carries `id` (`evt_01kz…`) and `X-Webhook-Request-Id`; stability across real messages requires pairing. |
| Inbound replay | **PENDING** | Unique event id + request id observed on every delivery; true redelivery dedup untested. |
| Ambiguous send handling | **PENDING** | `message.ack` exists (DOC); no send executed. |
| Session persistence | **PASS (SPIKE)** | Sessions **and** their webhook/HMAC config survived a full `docker restart`; a `FAILED` session auto-recovered to `SCAN_QR_CODE`. |
| Single-holder safety | **PARTIAL (DOC)** | Worker/restart model documented; competing-holder behaviour not exercised. Mitigated by the repository's own lease + fencing token in `channel_sessions`. |
| QR lifecycle | **PASS (SPIKE)** | `STARTING → SCAN_QR_CODE`; genuine 292×292 PNG and raw `wa.me/settings/linked_devices` value; rotation observed (~60 s first QR); exhaustion after 6 codes → `FAILED`. |
| Reconnect behavior | **PASS (SPIKE)** | `stop → STOPPED`, `start → SCAN_QR_CODE` recovery; configurable constant/linear/exponential retry with jitter. |
| History sync | **PASS (routes, SPIKE)** | `/api/{s}/chats` and `/api/{s}/chats/{id}/messages` present (HTTP 422, not 404). Cursor stability **PENDING**. |
| Live events | **PASS (SPIKE)** | Four webhooks delivered to a local receiver: `session.status` ×2, `state.change` ×2. |
| Media | **PASS (routes, SPIKE)** | `sendImage`, `sendFile` present. Byte transfer **PENDING**. |
| Health | **PASS (SPIKE)** | `GET /health` returns structured `status/info/error/details` incl. media and session storage headroom; `GET /ping`; `GET /api/server/status`. |
| Error model | **PASS (SPIKE)** | Cleanly distinguishable: `401` unauthenticated, `400` validation, `422` wrong-state with machine-readable `{error, status, expected:[…]}`. |
| Security | **PASS (SPIKE)** | `X-Api-Key` enforced (401 without key, 401 wrong key, 200 correct). Hashed (`sha512:`) keys and session-scoped keys with per-action grants supported. No plaintext session material returned by any inspected endpoint. |
| Tenant isolation | **PASS (SPIKE)** | Distinct QR per session; destructive operations on one session left the others untouched. |
| Operational support | **PASS (DOC)** | Apache-2.0, active public repository and release cadence, documented version policy. |
| Testability | **PASS (SPIKE)** | Whole evaluation executed in an isolated local Docker environment. |

**Tally: 13 PASS, 1 PASS-with-class-restriction, 1 PARTIAL, 4 PENDING, 0 FAIL.** No criterion failed
on technical grounds. Every PENDING item is blocked only by the absence of a paired handset.

## Certification evidence executed

Isolated `docker compose` deployment: dedicated bridge network, published on `127.0.0.1:3111` only,
`WAHA_DASHBOARD_ENABLED=false`, no link to the application stack, torn down with `down -v` after use.
Nothing from the spike was committed.

1. Container boots cleanly · 2. `/health` structured · 3. Sessions created · 4. **Genuine scannable
QR generated** · 5. QR rotation and 6-code exhaustion · 6. Session state API · 7. stop/start recovery
· 8. logout/delete semantics (`DELETE` → subsequent `404`) · 9. **Webhook contract captured with
`X-Webhook-Hmac` SHA-512 verified against the raw body on every event** · 10. **Required zero changes
to frozen application code.**

## Evidence not obtainable — physical phone pairing

Deliberately **not** simulated or asserted. All of the following remain uncertified:

- successful QR scan reaching `WORKING`;
- real inbound message receipt;
- outbound send;
- delivery/read acknowledgement (`message.ack`);
- real media transfer;
- history retrieval and cursor stability.

## Mandatory operating constraints

Binding on every later QR milestone:

1. **Internal network only.** WAHA must never be published to a public network or reverse-proxied to
   the internet. Its own documentation warns against public exposure.
2. **Protected session storage.** The provider's session volume holds live WhatsApp session material
   and must be access-restricted and encrypted at rest.
3. **QR values are credentials.** A QR payload is the pairing secret. It must never be persisted,
   logged, audited, cached or returned outside the authorized, short-lived, no-store pairing
   response. `assert_no_secret_material()` already exists to enforce this class of rule.
4. **Kill switch.** An operator-accessible emergency disable must exist before production enablement
   (ADR-0021).
5. **Prohibited capabilities.** The adapter must **not** declare `BULK`, `CAMPAIGNS` or `TEMPLATE`.
   QR must never be usable for campaigns, broadcasts or bulk/unattended sending (ADR-0020 §5,
   ADR-0021, Doc 33 §5).
6. **No automatic failover.** A Meta message is never silently resent via QR, nor the reverse.
7. **Disabled-by-default flags.** `omnichannel_qr_provider` / `omnichannel_qr_auth` remain off and
   organization-scoped.
8. **Acceptable-loss numbers only.** Per the owner's acceptance, only numbers whose restriction or
   permanent loss is acceptable may be connected.

## Residual risk — accepted by the owner

The dominant risk is **not** technical. WAHA drives the unofficial WhatsApp Web multi-device
protocol. WhatsApp does not sanction unofficial clients, and a connected number may be restricted or
permanently banned at any time. No engineering control in this repository mitigates that. It is
accepted explicitly and in writing by the owner above, scoped to internal single-organization use and
to numbers whose loss is acceptable.

## Adapter certification result

**Not applicable at QR-00.** No WAHA adapter, client, runtime, container service, provider
registration, QR API or UI exists in the repository. This record selects a candidate and authorizes
QR-01 to begin; it does not certify an implementation that has not been written.

## Outcome

**CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED.**

Prerequisites before production enablement:

1. Dedicated, disposable WhatsApp account and representative device (evaluation items E-007/E-008/E-009).
2. Completion of the four PENDING Required criteria against that device.
3. SBOM/provenance and vulnerability review of the pinned image digest (E-012).
4. Architecture conformity review (E-013).
5. Monitoring, alerting, kill-switch and rollback evidence (E-014).
6. Pin an immutable image digest; `latest` must not be used in production.
