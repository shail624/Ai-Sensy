# WAHA Class B Provider Evaluation Evidence

- **Repository:** `shail624/Ai-Sensy`
- **Branch baseline:** `ui/taste-modernization` at `a313eca4a6b8d65c78b33fe23404b74e9dc7b0f8`
- **Evaluation date:** 2026-08-05
- **Provider:** WAHA
- **Provider class:** Class B — Owner-approved Internal Self-hosted Provider
- **Requested version:** `<EXACT VERSION>` — not resolved to an immutable release, tag, package version or image digest
- **Deployment scope:** Internal, self-hosted, single organization, not SaaS, not resold
- **Certification test account:** Dedicated non-production WhatsApp account required; account evidence not supplied
- **Representative device:** `<Model Name>` — not supplied
- **Android version:** `<Version>` — not supplied
- **WhatsApp application:** Latest supported application requested; installed application version evidence not supplied
- **Evaluation outcome:** **Requires Additional Evidence**
- **Certification status:** **Not Certified**
- **M13-06 status:** **Blocked**

## Authority and evaluation boundary

This is provider-evaluation evidence only. It does not modify ADR-0020, ADR-0021, Design Document 33,
repository policy, architecture or roadmap sequencing. It does not approve an adapter, dependency,
runtime, QR login, inbound processing, history synchronization, media processing or M13-06.

The evaluation is governed by:

- `docs/adr/0020-enterprise-omnichannel-channel-manager.md`;
- `docs/adr/0021-provider-authorization-classes.md`;
- `docs/design/33-MODULE-13-ENTERPRISE-OMNICHANNEL-IMPLEMENTATION-CONTRACT.md`.

The owner authorized evaluation of WAHA only. No alternative provider was evaluated.

## Intake determination

The evaluation cannot execute against an exact candidate build because the owner instruction retains
literal placeholders for the WAHA version, device model and Android version. The repository also has
no supplied evidence identifying:

- an immutable WAHA release tag, package version or container-image digest;
- the dedicated certification account identifier or custody record;
- the representative Android device model;
- the representative Android operating-system version;
- the installed WhatsApp application version;
- a controlled test environment or runtime deployment for the candidate.

Provider capabilities must not be inferred from another WAHA release, a floating image tag, general
product documentation or a different device. Every Required criterion therefore remains unevaluated
unless repository evidence below explicitly proves it.

## Required criterion evaluation

A Required criterion is PASS only when evidence exists for the exact candidate version and approved
test environment. Unknown, unsupported or unevidenced criteria cannot pass.

| Required area | Result | Evidence / finding |
|---|---|---|
| Legal and policy position | REQUIRES ADDITIONAL EVIDENCE | Class B evaluation is owner-authorized, but exact-version licensing, data-processing terms and operational/policy Risk Acceptance were not supplied. |
| Stable identity | NOT EVALUATED | Requires exact-version runtime and representative-device evidence. |
| Message identity | NOT EVALUATED | Requires controlled inbound/outbound message-ID and idempotency testing. |
| Inbound replay | NOT EVALUATED | Requires duplicate/redelivery tests against the exact event implementation. |
| Ambiguous send handling | NOT EVALUATED | Requires acknowledgement-loss and reconciliation tests proving no blind resend. |
| Session persistence | NOT EVALUATED | Requires restart, restoration and safe re-pair evidence for the exact release. |
| Single-holder safety | NOT EVALUATED | Requires concurrent-runtime and stale-holder tests. |
| QR lifecycle | NOT EVALUATED | Requires pair, expiry, refresh, success, invalidation, logout and remote-logout evidence. |
| Reconnect behavior | NOT EVALUATED | Requires bounded reconnect, storm control and re-authentication evidence. |
| History sync | NOT EVALUATED | Requires bounded pagination/checkpoint, ordering, resume and duplicate-suppression evidence. |
| Live events | NOT EVALUATED | Requires event reliability and reconnect tests. |
| Media | NOT EVALUATED | Requires secure inbound/outbound media, type, size and failure tests. |
| Health | NOT EVALUATED | Requires factual connection/session health and alert-source evidence. |
| Error model | NOT EVALUATED | Requires retryable, throttled, authentication and terminal failure classification evidence. |
| Security | NOT EVALUATED | Requires secret/session isolation, redaction, runtime-only plaintext and supply-chain evidence. |
| Tenant isolation | NOT EVALUATED | Requires one-organization binding and cross-tenant denial evidence. |
| Operational support | NOT EVALUATED | Requires exact-version policy, incident path, maintenance and security-update process. |
| Testability | FAIL — INTAKE INCOMPLETE | Exact candidate version, test deployment, account and representative-device details are absent. |

No Required criterion has been marked PASS.

## ADR-0021 Class B control evaluation

| Class B control | Result | Finding |
|---|---|---|
| Owner Approval | PARTIAL | Owner approved WAHA as the sole evaluation candidate, not certification or production use. |
| Architecture Approval | REQUIRES ADDITIONAL EVIDENCE | No candidate-specific architecture review exists. |
| Security Approval | REQUIRES ADDITIONAL EVIDENCE | No candidate-specific security review or test evidence exists. |
| Risk Acceptance | REQUIRES ADDITIONAL EVIDENCE | No signed operational and policy Risk Acceptance exists for an exact version. |
| Feature Flag | NOT EVALUATED | No provider implementation or runtime was authorized. |
| Internal Deployment | SCOPE DECLARED | Must be verified in the eventual deployment. |
| Self Hosted | SCOPE DECLARED | Must be verified in the eventual deployment. |
| Single Organization | SCOPE DECLARED | Must be technically enforced and tested. |
| No Public SaaS | SCOPE DECLARED | No public deployment was evaluated or authorized. |
| No Resale | SCOPE DECLARED | No reseller deployment was evaluated or authorized. |
| Audit Coverage | NOT EVALUATED | Candidate-specific actions and runtime events were not integrated or tested. |
| Monitoring | NOT EVALUATED | Heartbeat, health, pairing, reconnect, history, media and split-brain alerts were not tested. |
| Kill Switch | NOT EVALUATED | No runtime exists against which disablement can be proven. |
| Runtime Isolation | NOT EVALUATED | No exact-version runtime deployment exists. |
| Tenant Isolation | NOT EVALUATED | No deployment exists for cross-tenant and organization-binding tests. |
| RBAC | NOT EVALUATED | No provider-specific command surface exists. Existing repository RBAC remains unchanged. |
| Evidence-based Certification | FAIL — INCOMPLETE | Exact-version and environment evidence is absent. |

## Technical evaluation

**Result: Requires Additional Evidence.**

No exact-version artifact was provided. Technical capability, protocol behavior, event semantics,
message identity, history behavior, media behavior, health reporting, error classification, restart,
reconnect and runtime ownership were not tested and are not inferred.

## Security evaluation

**Result: Requires Additional Evidence.**

No exact-version artifact, SBOM, image digest, vulnerability report, provenance record, secret-flow
review, session-material handling test, logging/redaction test, internal-authentication test,
least-privilege runtime configuration or cross-tenant denial test was provided.

The candidate must not be enabled, paired with a production account or represented as secure or
certified on the basis of this record.

## Architecture evaluation

**Result: Requires Additional Evidence.**

No adapter or dependency was introduced. The frozen repository authorities remain unchanged. A later
candidate-specific review must prove that WAHA can operate behind the existing `ChannelAdapter`,
connection, endpoint, session, runtime, queue, message, media, Contact, Audit, RBAC and tenant
authorities without introducing parallel ownership.

## Operational evaluation

**Result: Requires Additional Evidence.**

No operational deployment exists. Monitoring, alert routing, kill switch, backup/recovery, session
restoration, runtime replacement, incident response, upgrade/rollback, capacity, support, maintenance
and disaster-recovery procedures were not tested.

## Risk register

| ID | Risk | Severity | Current treatment | Closure evidence required |
|---|---|---:|---|---|
| R-01 | Candidate version is undefined, allowing evidence from a different build to be misapplied | Blocker | Fail closed | Immutable release/version and artifact digest |
| R-02 | Representative device and Android version are undefined | Blocker | Fail closed | Device model, Android version and installed WhatsApp version |
| R-03 | Dedicated non-production account is not evidenced | Blocker | Do not pair | Test-account custody and non-production confirmation |
| R-04 | Licensing and data-processing terms are not reviewed for the selected release/deployment | Blocker | Do not certify | Reviewed terms and recorded decision |
| R-05 | Operational and policy risk acceptance is absent | Blocker | Do not certify | Explicit owner Risk Acceptance after evidence review |
| R-06 | Message replay or acknowledgement ambiguity may cause duplicate customer sends | Critical | No outbound testing beyond controlled certification | Reconciliation and fault-injection evidence |
| R-07 | Competing runtimes may create split-brain session ownership | Critical | No runtime enablement | Multi-runtime lease/fencing and stale-holder rejection evidence |
| R-08 | Session material may be exposed through storage, logs, diagnostics or backups | Critical | No candidate deployment | Secret-flow, redaction, memory-only and backup evidence |
| R-09 | Protocol or WhatsApp application changes may invalidate behavior | High | Exact-version certification required | Compatibility matrix and re-certification triggers |
| R-10 | Missing monitoring or kill-switch behavior may delay containment | Critical | No production operation | Alert and emergency-disable test evidence |
| R-11 | Cross-tenant or cross-organization access may expose customer data | Critical | Single-organization scope does not waive controls | Object authorization and tenant-isolation tests |
| R-12 | Unsupported upgrades may silently exceed certification scope | High | Automatic upgrades prohibited by frozen governance | Pinned version/digest and tested rollback |

All Blocker and Critical risks remain open.

## Evidence register

| Evidence ID | Evidence | Status |
|---|---|---|
| E-001 | ADR-0020 frozen provider and architecture gate | Available |
| E-002 | ADR-0021 Class B authorization-class decision | Available |
| E-003 | Design Document 33 Required criteria and selection-record contract | Available |
| E-004 | Owner instruction selecting WAHA as the only Class B evaluation candidate | Captured by this repository record |
| E-005 | Exact WAHA version and immutable artifact digest | Missing |
| E-006 | Exact-version license and data-processing review | Missing |
| E-007 | Dedicated non-production certification-account evidence | Missing |
| E-008 | Representative device model and Android version | Missing |
| E-009 | Installed WhatsApp application version and linked-device evidence | Missing |
| E-010 | Controlled runtime deployment manifest and configuration | Missing |
| E-011 | Required technical test results | Missing |
| E-012 | Security assessment, SBOM, provenance and vulnerability evidence | Missing |
| E-013 | Architecture conformity review | Missing |
| E-014 | Operations, monitoring, kill-switch, recovery and rollback evidence | Missing |
| E-015 | Approved residual-risk record | Missing |

## Certification recommendation

**Do not certify.**

The candidate is not rejected on an evidenced technical failure because exact-version testing has not
begun. Certification cannot be prepared for owner approval because the evaluation intake is incomplete
and every technical Required criterion remains unevaluated.

## Final outcome

**REQUIRES ADDITIONAL EVIDENCE**

Evaluation may resume only for WAHA after repository evidence supplies:

1. the exact immutable WAHA version and artifact digest;
2. the dedicated non-production certification account;
3. the representative device model and Android version;
4. the installed WhatsApp application version;
5. the controlled self-hosted deployment details required to execute the frozen test matrix.

No alternative provider may be substituted under this evaluation record. No version may be changed
without a new explicit owner decision. M13-06 remains blocked.
