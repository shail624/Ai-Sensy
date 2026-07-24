# ADR-0006 — Keep deployed-stack verification isolated and focused

- **Status:** Accepted — 2026-07-25
- **Scope:** Module 11 E2E, deployment smoke, performance regression
- **Runtime/API/schema change:** none

## Context

Docs 10 §§4/26/36/43/47 require key real-UI journeys before staging and a performance-regression
check before production. The existing 892 backend and 581 frontend tests were intentionally
hermetic, while the release profile validated images without starting MySQL, Redis, Celery, the SPA,
and nginx together. Full capacity certification belongs in an isolated Performance Lab and must not
be misrepresented by a short workstation gate.

## Decision

- Add a cumulative `deployed` quality profile after `release`. It creates a unique Compose project,
  random synthetic secrets, an ephemeral host port, and project-scoped volumes; it always tears that
  exact project down with its volumes.
- Reuse `docker-compose.production.yml` and the already built application images. No second topology,
  test-only product route, altered permission model, or alternate database path is introduced.
- Build the browser runner from Playwright 1.61.1's official Chromium image pinned by immutable
  multi-platform digest. Its TypeScript test dependencies are exact and independently audited.
- Bootstrap an isolated Owner through the existing CLI, then drive one focused journey through the
  real nginx-served SPA: sign in, upload/map/start a CSV contact import, observe worker completion,
  find the persisted contact, and open its profile. This crosses nginx → SPA → API → MySQL → Redis
  broker → Celery jobs worker without sending to a real customer or provider.
- After the journey, make 5 warm-up and 30 measured authenticated standard reads through nginx.
  Block when nearest-rank p95 is not below Doc 1's 300 ms target. Emit JSON latency evidence and
  Playwright JUnit/trace/screenshot/video evidence under ignored `.quality-artifacts/`.
- Pin the remaining production MySQL image by manifest digest and make the release contract reject
  any unpinned third-party service image.

## Consequences

- The production topology, migration ordering, audited MySQL driver, worker routing, browser UI, and
  frozen read-latency target now execute together in a repeatable blocking gate.
- The first passing run completed the browser journey and observed a 7.9 ms p95 across 30 reads on
  the local isolated stack; future runs replace this point-in-time evidence.
- The gate downloads a large browser image once and requires Docker resources sufficient for the ten
  production services. Cached later runs are substantially faster.
- This is a regression canary, not load/stress/spike/soak or 1M-contact certification. Full
  Performance Lab, provider-sandbox, observability, rollback, UAT, TLS, backup/restore, and host
  commissioning evidence remain separate release criteria.
