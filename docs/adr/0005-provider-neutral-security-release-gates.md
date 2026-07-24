# ADR-0005 — Keep quality gates provider-neutral and security evidence reproducible

- **Status:** Accepted — 2026-07-25
- **Scope:** Module 11 hardening, dependency security, release automation
- **Runtime/API/schema change:** production MySQL driver only; no API, route, permission, schema, or business change

## Context

Docs 8 §43 and 10 §§4/47 make lint, types, tests, contracts, security scans, image checks, and
release smoke blocking at progressively heavier cadences. They deliberately define architecture,
not vendor-specific pipeline YAML. The repository previously held the individual commands and
point-in-time Docker evidence but no single executable contract that a workstation or any CI
provider could invoke.

The first dependency audit also identified `asyncmy` 0.2.11 as affected by the critical,
unpatched SQL-injection advisory
[GHSA-qhqw-rrw9-25rm](https://github.com/advisories/GHSA-qhqw-rrw9-25rm). Leaving the driver in
the production dependency graph or suppressing the advisory would violate the release criteria.

## Decision

- `scripts/quality_gate.py` is the provider-neutral entry point. `static`, `pre-merge`, and
  `release` profiles are cumulative and fail at the first red gate.
- The static profile runs backend Ruff and strict mypy, OpenAPI drift validation, and frontend
  ESLint and TypeScript checks. Pre-merge adds both full test suites, the frontend production
  build, Bandit SAST, backend and frontend dependency audits, and a tracked-source Trivy scan.
- The release profile additionally renders and validates both Compose models, builds the existing
  application images, verifies their non-root/health/smoke contracts, scans them for every open
  HIGH or CRITICAL vulnerability, and emits CycloneDX SBOMs.
- Trivy runs from the official 0.72.0 multi-platform image pinned by immutable manifest digest.
  It scans a temporary snapshot made only from Git-tracked and non-ignored candidate files, so a
  developer's ignored production environment file is never mounted into or copied to the scanner.
- Generated JSON and CycloneDX evidence lives in ignored `.quality-artifacts/`; the scanner cache
  lives in ignored `.quality-cache/`. CI retains these as run artifacts. Stale scan output is not
  committed as evidence of a later release.
- No high/critical or unpatched finding is implicitly ignored. Any future exception requires a
  separate, expiring, reviewed risk-acceptance decision; this milestone introduces none.
- Production image tags are now required and the checked-in example demonstrates `1.0.0-rc1`
  instead of mutable `latest`.
- Every application Dockerfile stage is pinned by immutable manifest digest. The backend and
  frontend runtime stages use current Alpine-based Python/nginx layers; production Redis and edge
  nginx are also digest-pinned. The Node build stage upgrades its bundled npm to a reviewed pin,
  and no Node tooling is copied into the frontend runtime.
- Replace `asyncmy` with SQLAlchemy's `aiomysql` dialect, pinning `aiomysql` 0.3.2 and its PyMySQL
  escaping layer at 1.2.0. The connection remains async MySQL and every repository/service/API
  boundary is unchanged.

## Consequences

- Local and automated execution share one reviewed gate definition without committing to GitHub,
  GitLab, or another CI product.
- Network access is required for live advisory data; Docker is additionally required for Trivy
  and the release profile. The offline `static` profile remains fast and deterministic.
- A release run produces current machine-readable SAST, vulnerability, and SBOM evidence and
  refuses mutable application tags, unpinned application base stages, root application images,
  contract drift, or high/critical findings in tracked source and built application images.
- Moderate frontend React Router advisories remain visible in audit output but are not blocking
  under the documented HIGH/CRITICAL release threshold. Their fixed line requires a v7 migration,
  so that upgrade stays explicit technical debt instead of being folded into hardening work.
- Real-browser/full-stack E2E, performance-lab certification, observability deployment, UAT, TLS,
  backups, and host commissioning are separate later gates; this ADR does not claim them complete.
