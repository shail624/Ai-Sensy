# Repository Rules

These rules govern every future milestone in this repository. They are subordinate only to an
explicit owner instruction. Product intent is controlled by
`VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`; implementation truth and remaining work are controlled by
`CURRENT_PROJECT_GAP_ANALYSIS.md` plus the latest approved Git HEAD.

## Source-of-truth hierarchy

1. GitHub is the only authoritative repository and delivery source of truth.
2. `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` is the permanent final-product specification.
3. `CURRENT_PROJECT_GAP_ANALYSIS.md` is the permanent baseline for distinguishing completed work
   from remaining work.
4. The latest approved Git HEAD is the implementation baseline. Always continue from it.
5. `IMPLEMENTATION_TRACKER.md`, `PROJECT_STATE.md`, `VALIDATION_RESULTS.md`, `MODULE_STATUS.md`,
   `ROADMAP.md`, and `CHANGELOG.md` are synchronized governance records, not substitutes for Git.
6. If records conflict, stop, verify the latest approved GitHub HEAD, and reconcile the governance
   files without silently changing either source-of-truth document.

## Preservation rules

- Never recreate completed work.
- Never rebuild existing modules. Extend the verified implementation only for an approved gap.
- Never duplicate completed modules or introduce parallel models, APIs, services, pages, or state.
- Never modify completed milestones or rewrite their historical evidence.
- Never inspect cached repositories.
- Never inspect or rely on cached repositories, ZIP archives, or previous snapshots. Only material
  committed to the latest approved GitHub HEAD may govern implementation.
- Never import excluded AiSensy surfaces or behavior. Ads Manager, WhatsApp Payments, SaaS billing,
  public signup, reseller/multi-project features, upgrade/trial promotions, and an integration
  marketplace remain prohibited.
- Use AiSensy reference material for permitted layout and workflow inspiration only. Preserve this
  product's own premium dark-green identity, accessibility, domain rules, and approved scope.

## Additive engineering invariants

- Never downgrade, renumber, squash, or rewrite applied migrations. New schema work is additive from
  the current migration head.
- Never reduce the OpenAPI path count unless the owner explicitly approves a documented breaking
  change.
- Never remove, skip, weaken, or silently quarantine tests.
- Preserve repository/service/API layering, tenant isolation, RBAC, auditability, generated API
  contracts, and the existing queue/send/retry authorities.
- Generate TypeScript API contracts from backend OpenAPI. Never hand-write competing contract types.
- Keep incomplete functionality honest: no fake success states, invented metrics, or executable-looking
  placeholders.

## Required milestone closeout

Every milestone must:

1. Start from the latest approved Git HEAD and verify the worktree before editing.
2. Implement only the milestone approved by the owner.
3. Run the validation gates applicable to the change and record truthful results using only `PASS`,
   `FAIL`, or `PENDING – Host Machine Validation`.
4. Update `CHANGELOG.md`.
5. Update `IMPLEMENTATION_TRACKER.md`.
6. Update `PROJECT_STATE.md`.
7. Update `VALIDATION_RESULTS.md`.
8. Update `MODULE_STATUS.md`.
9. Update `ROADMAP.md` when estimates, sequencing, dependencies, or completion state change.
10. Keep the source-of-truth documents unchanged unless the owner explicitly approves an intent
    change.

Exactly one milestone is allowed per commit. Do not combine unrelated milestones in one commit and
do not spread one milestone across multiple commits without owner approval. Stop after each
milestone and wait for user approval before the next milestone.

## UI reference boundary

Only UI requirements and permitted interaction patterns recorded in the GitHub repository may be
used. Ads, payments, billing, partner marketplaces, SaaS controls, public signup, reseller tooling,
and other excluded functionality must not be implemented regardless of any external reference.

## Definition of synchronized

The governance files are synchronized when their branch, recorded HEAD, version, migration head,
OpenAPI count, test evidence, milestone labels, module percentages, validation results, roadmap
status, and changelog entry agree with the worktree being handed to the owner. A milestone is not
ready for approval while these records disagree.
