# ADR-0022 — Patch pinned runtime images during release builds

## Status

Accepted — 2026-09-21.

## Context

Digest-pinned Alpine base images made builds reproducible but retained system packages for which
the same Alpine release already published security fixes. The blocking image scan correctly
rejected the deployable backend and frontend images.

## Decision

Keep the immutable base-image digests and run the distribution's no-cache security upgrade in
each final runtime stage. Continue to fail release promotion on any high/critical image finding
and generate an SBOM for each deployable image.

The deployed browser gate may override the auth request maximum only inside its disposable
Compose project because its hard-navigation crawler rotates more tokens than a user workflow.
The production Compose default remains ten.

## Consequences

Build output stays traceable to an immutable base while consuming fixed packages available in its
repository at build time. A release build therefore requires repository availability and must be
rescanned; the resulting image digest and SBOM, rather than the base digest alone, are the release
artifact. The test-only auth allowance cannot silently become the production default.
