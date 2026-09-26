# ADR-0021: Provider Authorization Classes for Internal Self-hosted Deployment

- **Status:** Accepted and frozen
- **Date:** 2026-08-05
- **Amends:** ADR-0020 provider selection boundary only
- **Decision owner:** Repository owner
- **Implementation status:** Documentation only; no provider selected or approved

## Context

ADR-0020 and Design Document 33 correctly require evidence-based provider certification and fail
selection when any Required criterion is unsupported or cannot be evidenced. The existing gate also
requires a documented authorization position. The repository owner has approved two provider classes
without changing the provider-neutral architecture or weakening security, RBAC, tenant isolation,
Audit, runtime isolation, repository quality, or any technical Required criterion.

## Decision

Provider certification distinguishes the following classes:

- **Class A — Official Providers.** Official providers, including Meta Cloud API, must satisfy every
  existing ADR-0020 and Design Document 33 Required criterion exactly as written. The authorization
  evidence is documented official authorization together with reviewed licensing and data-processing
  terms.
- **Class B — Owner-approved Internal Self-hosted Providers.** A Class B provider is not official and
  must never be represented as officially authorized. The existing authorization criterion remains
  Required, but its accepted evidence for this class is an explicit owner-approved internal
  self-hosted deployment decision together with Architecture Approval, Security Approval, reviewed
  licensing and data-processing terms, and explicit operational and policy Risk Acceptance.

Class B certification additionally requires all of the following:

- named and versioned provider evidence evaluated for the exact deployment;
- Internal Deployment and Self Hosted operation for a Single Organization only;
- no Public SaaS, multi-customer hosting, marketplace distribution, reseller use, or Resale;
- disabled-by-default, organization-scoped Feature Flag protection;
- unchanged RBAC, Tenant Isolation, object authorization, and Audit Coverage;
- isolated runtime and secret handling with existing lease, fencing, and session controls;
- operational Monitoring, alerting, and an effective emergency Kill Switch;
- Owner Approval, Architecture Approval, Security Approval, and Risk Acceptance recorded in the
  certification evidence;
- Evidence-based Certification against every other existing Required criterion.

Unsupported, unknown, or unevidenced Required criteria remain certification failures. Class B does
not permit QR campaigns, broadcasts, bulk automation, automatic cross-provider failover, public
service, or weaker operational controls.

## Consequences

- ADR-0020's architecture, provider-neutral adapter seam, security controls, certification strength,
  and all technical Required criteria remain unchanged.
- The legal and policy authorization evidence is class-specific: official authorization for Class A;
  explicit owner-approved restricted internal deployment for Class B.
- No provider is selected, preferred, approved, or certified by this ADR.
- WAHA, Evolution API, and every other candidate remain unevaluated and uncertified.
- M13-06 remains blocked until a specific candidate passes the applicable class evidence and every
  existing Required criterion, its certification record is approved, and a separate owner
  instruction authorizes further work.
- Roadmap sequencing, implementation status, runtime code, API, migrations, dependencies, generated
  contracts, build output, and product behavior are unchanged.

## Validation boundary

Applicable validation is documentation-only: latest remote baseline verification, Markdown
structure, mandatory-control presence, additive ADR numbering, and confirmation that ADR-0020,
Design Document 33, ROADMAP.md, runtime code, API, migrations, dependencies, generated contracts,
and build output are unchanged.

Backend and frontend tests, builds, browser checks, migration execution, OpenAPI generation,
dependency audits, runtime commissioning, and host validation are not applicable because this
decision changes no executable artifact or milestone status. GitHub Actions scheduling was
unavailable from the current environment and is not treated as successful evidence.
