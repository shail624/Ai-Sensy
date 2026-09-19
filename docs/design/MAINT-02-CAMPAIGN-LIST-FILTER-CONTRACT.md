# MAINT-02 — campaign list filter contract

Approved scope: declare q and status, regenerate contracts, use server filtering in the
existing campaign list and verify valid/invalid/tenant behavior. Pagination is explicitly
excluded by the owner. Frozen design documents remain unchanged.

Before implementation, the approved branch's generated live operation had no query
parameters. Frozen API design section 17 explicitly requires status and q filtering;
the implementation's direct request lookup hid those parameters from generated clients.
The existing repository already implements these filters within organization/deletion scope.

The route now declares nullable string Query parameters. A validation pattern is derived
from the existing campaign status tuple, so invalid states return 422 without maintaining
another status vocabulary. The legacy filter spelling remains validated and retains its
existing precedence. Only q/status are published as the supported generated client query.

Frontend filter types are aliases of generated types. Search/status participate in query
identity. Other hook consumers retain their unfiltered and enabled/disabled behavior.
Results are no longer filtered again locally; existing sort/slice behavior is preserved.
Loading retains filter controls, and filtered zero results use the no-match state.
No old-query placeholder rows are displayed as results of a newly selected filter.

Former local-filter tests now assert that server results are authoritative; filtering
coverage resides at the backend boundary plus generated-client hook/list regressions.
No tests were skipped or quarantined.

Acceptance: 962 backend tests, 657 frontend tests including 48 campaign tests; focused new
backend checks 14; typecheck/build/lint, changed-file Ruff, endpoint mypy, schema drift pass.
193 paths and migration head 0035_notification_center unchanged. No deployment claim.
