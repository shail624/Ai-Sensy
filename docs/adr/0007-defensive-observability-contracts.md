# ADR-0007 — Verify defensive observability at the production boundary

- **Status:** Accepted — 2026-07-25
- **Scope:** Module 11 logging, correlation, readiness, deployed verification
- **Runtime/API/schema change:** no route or response-schema change

## Context

Docs 10 §§4/5/26/27/30/31 and Doc 8 §§18/19/24/25 require correlated structured logs,
safe handling of sensitive data, and health signals that reflect real dependency state. The
application already emitted JSON logs and exposed the frozen `/health` and `/ready` routes, but
the release gate did not prove correlation, redaction, or readiness degradation in the deployed
topology. Uvicorn's access logger also emitted a second, uncorrelated request record.

Metrics backends, log shipping, dashboards, alert firing, and traces are environment concerns.
Adding a second monitoring topology to the repository would not prove the production deployment
and would exceed this repository-verifiable milestone.

## Decision

- Treat the application middleware's `http_request` event as the canonical API access record and
  disable the duplicate Uvicorn access logger after application logging is configured.
- Accept a caller-supplied `X-Request-Id` only when it is a bounded safe token; otherwise generate
  a UUID. Apply the same rule at nginx, forward that id upstream, return it to the caller, and write
  it as `rid=` in the edge access log.
- Defensively redact sensitive field names plus recognizable bearer tokens, JWTs, live API keys,
  email addresses, and international phone numbers at both JSON and text formatter boundaries.
  Product code must still avoid logging sensitive values in the first place.
- Extend the existing isolated deployed-stack gate instead of creating a second topology. The gate
  proves that the edge and structured API request events share correlation ids, scans both outputs
  for its synthetic secret/PII values, stops Redis, and requires `/ready` to return 503 with Redis
  reported down.
- Validate the actual mounted nginx configuration with the exact digest-pinned production image as
  part of the release contract.

## Consequences

- Every canonical HTTP access event has a request id, method, path, status, and duration, while
  request-scoped application events inherit the same id through the existing context binding.
- Unsafe correlation headers can no longer inject arbitrary access-log content or unbounded values.
- Accidental secret/PII logging is reduced at the final output boundary without changing API
  routes, permissions, business behavior, queues, persistence, or the OpenAPI contract.
- The deployed gate now verifies the observable failure mode operators use for load-balancer
  removal; liveness remains deliberately dependency-free.
- Log shipping, dashboards, alert/dead-man evidence, traces, and synthetic external monitoring
  remain commissioning work for the target environment.
