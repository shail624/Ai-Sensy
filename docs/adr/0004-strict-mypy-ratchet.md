# ADR-0004 — Ratchet strict mypy findings without weakening the type policy

- **Status:** Superseded — 2026-07-25 (exit condition fulfilled)
- **Scope:** backend quality gates, Module 11 hardening
- **Runtime/API/schema change:** none

## Outcome

The ratchet served one bounded hardening increment and reduced the recovered 251 findings to 120.
The following increment made raw strict `mypy app` clean across all 227 backend source files. As
required by this decision's exit condition, the baseline, wrapper, and wrapper-specific tests were
then removed. Direct strict mypy is now the blocking type gate; this ADR remains as the historical
record of the transition rather than an active mechanism.

## Context

The backend already declares strict mypy configuration in `pyproject.toml`, documents `mypy app`
as a project check, and the Design Book makes Python type-checking a blocking pre-commit and CI
gate. The recovered repository nevertheless starts this hardening increment with 251 findings in 67
files. They span third-party Celery and SQLAlchemy typing seams, unparameterized JSON annotations,
and service/repository findings that may require explicit runtime guards.

Disabling strict mode, ignoring whole error classes, or treating the current failure as advisory
would hide new defects while the debt is being removed. Requiring all 251 findings to disappear in
one change would instead couple unrelated completed modules and encourage unsafe casts.

## Decision

Keep the existing strict mypy configuration unchanged and add a versioned, monotonic ratchet:

- `scripts/check_mypy.py` runs mypy using the repository configuration and parses only structured
  `error` diagnostics carrying an error code.
- Paths are normalized across Windows and Linux. The baseline records counts by source file and
  mypy error code; line movement and wording changes do not create noise.
- The normal gate requires an exact path/error-code allowance match. A new pair or higher count is
  a regression; a lower count marks the baseline stale until the explicit write command lowers it.
- A same-version baseline write refuses every increased allowance. A checker-version replacement
  requires a separate `--allow-version-change` flag and review of the full baseline diff.
- The raw finding total remains visible on every run. The ratchet is transitional and is deleted
  with its zero baseline once `mypy app` is clean.
- Strict rules are never globally disabled. Any localized cast or suppression must sit at a typed
  third-party boundary and remain reviewable in source.

The first reduction targets runtime-neutral, high-leverage seams: generic async/Celery execution,
JSON model annotations, and association-table option typing. Repository/service findings that may
change behavior are handled in later focused increments with their own tests.

## Alternatives rejected

1. **Turn off strict mode or disable failing error codes.** This makes the documented gate green by
   weakening it and permits new defects in every module.
2. **Check only the total error count.** One fixed error could mask one new error elsewhere.
3. **Baseline full messages and line numbers.** Harmless edits would churn the baseline and obscure
   meaningful changes.
4. **Fix every finding in one commit.** Several optional-result findings cross business boundaries;
   changing them safely requires focused behavioral tests rather than a bulk annotation pass.

## Consequences

- New or increased path/error-code allowances become blocking immediately.
- Existing debt is explicit, reviewable, and same-version allowances can only move downward.
- Path/error-code counting avoids churn from line movement and wording changes, but cannot
  distinguish replacing one same-code diagnostic with another in the same file. Requiring every
  decrease to update the baseline narrows that window; code review remains the backstop.
- The raw `mypy app` command remains the end-state signal; the ratchet does not claim the backend is
  fully type-clean until that command exits successfully.
- No endpoint, permission, route, queue, migration, database constraint, or provider behavior is
  changed by this decision.
