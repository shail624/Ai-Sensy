# REL-02A — Local release certification

**Status:** repository and disposable-host evidence complete on 2026-09-21. This is the local,
provider-neutral portion of REL-02; it is not target-host commissioning or real-provider UAT.

## Scope and boundary

This milestone runs the complete deployed quality profile: static analysis, full backend and
frontend suites, dependency/source/image security scans, SBOM generation, production image and
Compose contracts, certified WAHA adapter probes, and an isolated production stack with browser,
accessibility, performance, observability and Redis-degradation checks.

It does not certify a real Vi dataset, Meta/Google credentials, physical WhatsApp delivery,
off-host backup storage, million-contact capacity, soak testing, TLS, monitoring destinations or
the owner's target server. Those remain REL-02/REL-03 evidence and must never be inferred from a
local disposable stack.

## Findings and decisions

The release scan found fixed-version-available high-severity findings in Alpine packages carried
by both runtime images. The images retain reproducible base digests and now apply the current
security updates from that pinned Alpine release during the build. High/critical image scans then
passed and generated CycloneDX SBOMs.

The authenticated accessibility crawler also exhausted the intentional production auth bucket:
each hard route navigation creates a new document and rotates the memory-only access token. The
production default remains ten requests per five minutes. Only the disposable deployed gate sets
a higher allowance, so the test workload does not weaken the shipped security default.

## Acceptance evidence

- Backend lint, strict typing and OpenAPI drift: pass.
- Full backend suite: 1,782 passed.
- Full frontend suite: 63 files and 1,022 tests passed; TypeScript, lint and production build pass.
- Backend/frontend/browser dependency audits: zero known vulnerabilities at the blocking level.
- Source, secret and infrastructure scan: pass.
- Backend and frontend runtime image high/critical scans: pass; SBOMs generated.
- Production release contract: ten services, edge-only publication; both image contracts pass.
- Certified WAHA health, QR content negotiation and signed-webhook retry probes: pass without
  pairing, scanning or disclosing a QR/credential.
- Isolated deployed browser gate: five of five passed across light, dark, phone-width, signed-out
  accessibility and contact import/search.
- Performance canary: p95 6.1 ms across 30 reads against a 300 ms budget.
- Redis-stop readiness degradation and request-id/log-correlation checks: pass.

## Remaining release gates

REL-02 still needs an approved capacity dataset/lab for stress, spike, soak and million-contact
evidence plus a real off-host backup/restore drill. REL-03 still needs the target host, TLS,
production secrets, monitoring destinations, real provider/data credentials and owner UAT.
