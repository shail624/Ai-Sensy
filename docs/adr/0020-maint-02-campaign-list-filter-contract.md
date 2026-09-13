# ADR 0020 — expose existing campaign filters through the generated contract

Status: Accepted for owner-approved MAINT-02.
Date: 2026-09-13.

## Context

The frozen API design requires campaign-name and status filtering. The implementation
reads them from the request but omits typed declarations, leaving generated consumers
unable to express them. The frontend compensates by filtering complete responses.

## Decision

Declare optional q/status Query parameters; derive allowed status validation from the
existing status tuple. Preserve existing legacy filter compatibility and precedence.
Regenerate OpenAPI and TypeScript using the repository generators, then pass filters
through the generated client with distinct query-cache identity.
Remove only the duplicate name/status filtering; preserve local sorting and paging.

## Boundaries and consequences

No pagination or query bounds are introduced: those require separate owner approval.
No source-of-truth schema/API design edits, migrations or lifecycle changes.
Invalid status values now fail validation instead of returning misleading empty results.
Unfiltered existing hook consumers continue to work.
Existing SQL matching semantics remain authoritative; no new case, wildcard or whitespace
normalization policy is introduced.
Contract generation may reorder JSON object keys without changing other operation semantics.

## Evidence

Live pre-change contract had no list query parameters. New contract tests require exactly
q/status; runtime tests cover every existing status, invalid values, combined filtering,
legacy compatibility and tenant isolation. Frontend tests cover request propagation,
query changes, denied/disabled fetching and correct filtered empty-state presentation.
