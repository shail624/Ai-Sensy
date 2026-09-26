# ACCEPT-01 — MySQL Migration Reversibility

Date: 2026-09-21  
Status: accepted

## Decision

The release migration chain must pass `base → head → base → head` on disposable MySQL 8. SQLite
round trips remain useful but are not sufficient evidence for production migration safety.

## Findings

The first clean MySQL upgrade exposed a required existing-type declaration when migration 0070
changed JSON-column nullability. The first complete rollback then exposed MySQL foreign-key/index
dependencies in historical migrations: some downgrades removed a unique or secondary index before
removing its dependent foreign key, or immediately before dropping the whole table.

## Resolution

- Declare the existing JSON type for the 0070 nullability change.
- Remove dependent foreign keys before their backing unique indexes.
- Create replacement foreign-key-supporting indexes before replacing a unique constraint.
- When a downgrade drops an entire table, let that table drop remove its indexes atomically rather
  than deleting possible foreign-key backing indexes first.
- Preserve child-before-parent table removal order.

These changes do not alter the schema produced at migration head and do not change application
contracts, permissions or user-visible behavior.

## Acceptance evidence

- Fresh disposable MySQL 8: 0001 through 0070 upgrade passes.
- Same database: complete downgrade to base passes.
- Same database: complete re-upgrade to 0070 passes.
- Dedicated live-MySQL regression covers head-to-base-to-head.
- Complete backend: 1,781 passed.
- Backend static gates: Ruff passed; strict mypy passed across 332 source files.
- Complete frontend: 63 files and 1,022 tests passed; TypeScript, ESLint and production build pass.

## Scope boundary

This milestone changes migration execution safety and its regression coverage only. It does not
change the head schema, API contract, generated frontend types, product UI, feature behavior or
deployment topology. Authenticated populated browser/mobile acceptance remains the next milestone.
