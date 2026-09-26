# UI-REF-04 — Live Chat category semantics

## Design and decision record

Status: locally implemented, 2026-09-14; release pending.

The owner explicitly defines Requests as open and unassigned, Active as open,
and My chats as current assignment ownership. The local reference-style UI had
instead selected pending status for Requesting and restricted Intervened to open.
This conflicts with the owner's stated product behavior regardless of reference labels.

Decision: retain the current caption order and layout, but use the owner's filter
semantics. Tooltips explain each category. Switching replaces status, assignment
and tag while preserving q. Overlap is intentional. No count is inferred from
the loaded page; future badges must use q plus tenant/permission scope only.

Boundary: category filter mapping and regression tests. No server mutation,
assignment lifecycle, API schema, migration or reference assets changed.

Evidence: 32 inbox tests PASS; TypeScript PASS. The new regression exercises
all three categories from contradictory filters with a retained search term.
Authenticated populated preview remains PENDING – Host Machine Validation.
Existing unrelated uncommitted implementation is preserved. No full-parity or
production-release claim is made by this small correction.
