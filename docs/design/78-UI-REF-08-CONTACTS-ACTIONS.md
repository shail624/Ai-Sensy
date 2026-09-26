# UI-REF-08 — Contacts actions and export discovery

Date: 2026-09-20

## Observed reference

The authenticated Contacts screen keeps Add, Import and Actions together above its selectable
table. Actions exposes export and history without requiring a selected row; selection-only edits
remain disabled until contacts are chosen.

## Implementation

- Contacts now has a permission-aware Actions menu beside Add Contact and Import.
- Export current view opens the existing governed export dialog with the active server-side rules.
  It does not pretend that selected rows define export scope.
- Export history opens the existing unified Download Center.
- The menu closes on outside click, Escape and navigation; Escape restores trigger focus.
- Existing selection-only tag, attribute, campaign and destructive actions remain in the bulk bar.
- No backend, API, model, migration, permission or new export implementation was added.

## Deliberate non-matches

Ads remain excluded. Import history is not labelled as available because the Download Center does
not yet prove unified import-job discovery. Add to List is not shown because there is no approved
standalone static-list domain. No disabled or executable-looking placeholder is introduced.

## Validation

- PASS: focused Contacts actions/filter/bulk suite, 19/19.
- PASS: full frontend, 62 files / 1,016 tests.
- PASS: TypeScript, ESLint and production build.
- PENDING – Host Machine Validation: authenticated representative-data desktop/mobile visual and
  export/download navigation acceptance.
