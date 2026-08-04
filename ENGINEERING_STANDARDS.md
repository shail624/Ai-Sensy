# Engineering Standards

This document is the permanent engineering and product-quality acceptance standard for this
repository. It consolidates the approved governance, UI, UX, browser, performance, operator,
security, workflow, and production-readiness rules so future prompts can remain short.

GitHub at the latest approved HEAD remains the implementation source of truth. This document does
not replace `REPOSITORY_RULES.md`, product scope, roadmap, or current-state records; it defines the
mandatory method and evidence required to deliver them.

## Permanent status model

Every milestone must use exactly one of these lifecycle states:

`Planned → In Progress → Implemented → Repository Validated → Host Validated → Production Ready → Released`

| Status | Meaning |
|---|---|
| Planned | Scope, dependencies, risks, acceptance criteria, and evidence plan are recorded; coding has not started. |
| In Progress | The approved milestone is actively being implemented from the latest Git HEAD. |
| Implemented | In-scope code and documentation are complete, but required validation is not yet fully passed. |
| Repository Validated | Every validation gate executable from the repository environment passes and governance is synchronized. Host-only evidence may still be pending. |
| Host Validated | Required screenshots, browser checks, real operator journeys, runtime performance, responsive, accessibility, and representative-data review pass on the target host. |
| Production Ready | Feature, UX, security, browser, performance, accessibility, workflow, parity, governance, and deployment-readiness gates all pass with no unresolved Blocker or Major issue. |
| Released | The approved commit has been deployed to production and deployment verification has passed. |

A milestone must never skip a status. When host-machine-only evidence cannot be produced in the
current environment, the highest honest status is normally `Repository Validated`; use `Blocked`
inside the milestone record when a mandatory failure or unresolved dependency prevents progress.
Never claim `Host Validated`, `Production Ready`, or `Released` without direct evidence.

## 1. Repository Governance

- GitHub is the only repository and delivery source of truth.
- Always continue from the latest approved Git HEAD. Never rely on cached repositories, old working
  copies, generated guesses, or previous implementation snapshots.
- Follow, in order, the permanent product scope, `REPOSITORY_RULES.md`, this document,
  `PROJECT_STATE.md`, and `ROADMAP.md`.
- Read the relevant module, architecture, ADR, design, validation, and governance records before
  modifying implementation.
- Preserve completed work. Extend existing architecture and authorities; do not recreate completed
  modules, create parallel models/services/APIs/pages, or rewrite historical evidence.
- Implement exactly one approved roadmap milestone per reviewed commit. Iterate within that milestone
  until no further safe, in-scope improvement remains; do not begin the next milestone without owner
  approval.
- Keep incomplete functionality honest. Do not invent data, success states, metrics, permissions,
  integrations, production evidence, or executable-looking placeholders.
- Owner-approved AiSensy material is a private workflow and quality benchmark only. Never copy code,
  markup, CSS, wording, branding, colors, icons, typography, assets, screenshots, proprietary
  behavior, or exact layouts.
- Product exclusions in the permanent scope remain excluded even when present in reference material.
- Record decisions, verified gaps, validation evidence, defects, accepted debt, and owner deferrals in
  the appropriate governance file.
- Freeze this process. Add or weaken a permanent rule only through explicit owner instruction.

## 2. Git Workflow

Use this delivery cycle for every milestone:

`Analyze → Plan → Implement → Validate → Fix → Revalidate → Update Governance → Commit → Push → Verify Remote HEAD → Stop`

Before coding:

1. Verify the target branch and latest remote HEAD.
2. Confirm the worktree/change boundary.
3. Inspect related modules, shared components, APIs, permissions, tests, and dependencies.
4. Identify risks, affected systems, compatibility constraints, and evidence requirements.
5. Create a small-step implementation plan aligned to the roadmap milestone.

During implementation:

- Prefer simple, maintainable, additive changes.
- Preserve repository/service/API layering, generated contracts, migration history, RBAC, tenant
  boundaries, auditability, queue/send/retry authorities, and established product workflows.
- Reuse or extend governed shared components before creating new primitives.
- Keep unrelated fixes out of the milestone unless they are verified, directly related, tested,
  reusable, and scope-neutral.
- Do not weaken, skip, quarantine, or silently remove tests.
- Do not use temporary product code, temporary migrations, hidden feature duplicates, or untracked
  production behavior.

Closeout:

- Run every applicable repository and host validation gate.
- Update required governance records truthfully.
- Use Conventional Commits.
- Produce one milestone commit unless the owner explicitly authorizes otherwise.
- Push to the approved remote branch.
- Verify the remote branch HEAD equals the reported commit SHA.
- Stop after the milestone reaches the highest status supported by available evidence.

## 3. UI Standards

The product must feel like an original, premium enterprise WhatsApp Business platform designed for
operator productivity, not a generic admin template, CRUD shell, or decorative dashboard.

Every materially changed screen must:

- Lead with operational decisions, priorities, blockers, exceptions, and primary actions.
- Preserve strong information hierarchy, enterprise density, visual scanning efficiency, and
  consistent spacing.
- Use the governed shared design system for typography, colors, radii, surfaces, controls, toolbars,
  filters, tables, pagination, dialogs, drawers, feedback, and responsive composition.
- Avoid decorative cards, excessive nested surfaces, gradients without meaning, over-rounded
  containers, empty dashboards, fake KPIs, and non-actionable charts.
- Provide truthful populated, loading, skeleton, empty, partial-data, error, offline, disabled,
  permission-denied, success, and recovery states as applicable.
- Provide smart search, filters, sorting, pagination, bulk actions, activity context, progress, and
  direct source actions where required by the workflow.
- Preserve navigation, product architecture, and business workflows unless the milestone explicitly
  approves a change.
- Use restrained, purposeful motion only. Do not introduce heavy animation libraries without an
  explicit architecture decision.
- Remain original while comparing workflow maturity, density, clarity, and usability against the
  approved reference.

Visual evidence for every materially changed primary screen must include actual running-application
captures at minimum:

- Desktop: `1920 × 1080`
- Mobile: approximately `390 px` wide

AI-generated images may support design exploration but are not implementation-validation evidence.
Review screenshots for spacing, density, alignment, wrapping, overflow, contrast, focus visibility,
touch targets, loading stability, empty/error states, drawers, tables, sticky elements, and mobile
transformation. Capture additional states when relevant rather than treating two populated-state
screenshots as sufficient evidence.

## 4. UX Standards

Every completed workflow must be evaluated from the perspective of a real operator. The interface
must optimize safe decision-making and task completion rather than appearance alone.

Review:

- Time to complete
- Clicks/taps
- Page transitions
- Context switches and backtracking
- Cognitive load
- Discoverability
- Information hierarchy
- Visual scanning effort
- Error prevention
- Recovery after mistakes
- Confirmation feedback
- Accessibility
- Mobile usability

Mandatory questions:

- Can a first-time operator understand the page within five seconds?
- Is the primary action immediately obvious?
- Can the workflow be completed without confusion?
- Can unnecessary clicks, transitions, scrolling, or repeated entry be removed safely?
- Is important information surfaced early enough?
- Can the operator make the required decision quickly and confidently?
- Can repetitive work be reduced through defaults, preserved context, bulk actions, shortcuts, or
  automation without weakening safety or auditability?
- Does the workflow feel appropriate for a ₹50,000/month enterprise product?

If any answer is `No`, continue improving within the approved milestone before closeout. Do not
remove deliberate confirmations, permission checks, or audit requirements merely to reduce clicks.

Classify findings:

- **Blocker:** workflow cannot be completed safely, critical information/action is inaccessible, or
  data/security integrity is at risk.
- **Major:** material confusion, excessive context switching, broken hierarchy, serious mobile or
  accessibility friction, or avoidable repeated work.
- **Minor:** non-blocking polish, spacing, wording, discoverability, or efficiency issue.

Resolve and retest all Blocker and Major findings before `Host Validated` or `Production Ready`.

## 5. Accessibility Standards

Accessibility is a completion requirement, not a later enhancement.

Verify as applicable:

- Semantic headings, landmarks, forms, tables, lists, status messages, buttons, and links
- Logical keyboard tab order and complete keyboard operation
- Visible, high-contrast focus states in light and dark themes
- Focus placement, trapping, restoration, and Escape behavior for dialogs and drawers
- Accurate accessible names, labels, descriptions, errors, required/invalid/busy/disabled states
- Screen-reader announcements for loading, validation, success, errors, partial data, and updates
- Skip links and efficient navigation of dense screens
- Sufficient color contrast without relying on color alone
- Touch targets suitable for mobile operation
- Responsive reflow without loss of content or action
- Reduced-motion support
- Zoom, text scaling, long labels, localization-length stress, and high-density content
- Accessible charts with meaningful labels or equivalent textual information
- Accessible empty, loading, error, permission, and read-only states

Keyboard-only completion must be possible for the primary workflow wherever the underlying action is
available. Hidden or visually disabled actions must not remain keyboard- or API-triggerable beyond
permission. Record automated accessibility evidence separately from manual keyboard and screen-reader
evidence.

## 6. Browser Validation

Every UI milestone must be validated in:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox

For each materially changed primary screen, validate desktop `1920 × 1080` and mobile approximately
`390 px` wide using the actual application and representative data.

Verify:

- Layout, spacing, density, alignment, and font rendering
- Sticky headers, sticky toolbars, and nested scrolling
- Tables, column sizing, truncation, overflow, and horizontal scrolling
- Drawers, dialogs, overlays, focus trapping, and scroll locking
- Hover, active, selected, disabled, and focus-visible states
- Keyboard navigation and shortcuts
- Page, panel, and virtualized scrolling
- Charts, labels, tooltips, resizing, and responsive fallback
- Responsive transformation, touch targets, and mobile navigation
- Loading, empty, error, partial-data, and long-content states

Record browser-specific issues separately:

```text
Browser:
Version:
Viewport:
Screen/workflow:
Issue:
Severity:
Steps to reproduce:
Expected:
Actual:
Screenshot/trace:
Resolution:
Retest status:
```

No unresolved browser-specific Blocker or Major issue is allowed at `Host Validated` or
`Production Ready`.

## 7. Performance Acceptance

Collect comparable evidence for every materially changed UI milestone:

- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP), including the LCP element
- Interaction responsiveness: INP when field/runtime evidence exists; otherwise relevant lab
  interaction timing and Total Blocking Time (TBT)
- Initial JavaScript and CSS bundle sizes
- Shared/vendor and route-specific chunk sizes
- Lazy-loaded chunks and their trigger points
- Cumulative Layout Shift (CLS) and render stability
- Loading-to-content transitions, scroll jumps, input delay, and visible jank

Measure at minimum:

- Initial authenticated load
- Warm navigation to the changed route
- Loading-to-populated transition
- Representative large-data state
- Primary interaction sequence, including filters/search/pagination or drawer/dialog use
- Mobile viewport

Use the same build mode, browser version, machine, data, viewport, and throttling profile when
comparing milestones. Record:

```text
Metric:
Previous milestone:
Current milestone:
Difference:
Status: Improved / Neutral / Regression
Reason:
Mitigation:
Follow-up:
```

A regression must not be hidden. Document its reason, product benefit, alternatives considered,
mitigation, and approved follow-up. Blocker or Major regressions must be fixed before production
readiness. Bundle evidence must distinguish main, vendor/shared, CSS, and lazy route chunks rather
than reporting only one total.

## 8. Operator Journey Review

Complete the primary workflow as a real operator using realistic permissions and representative data.
Define the journey before measuring:

```text
Operator role:
Tenant:
Starting screen/state:
Objective:
Completion condition:
Expected business outcome:
```

Measure:

- Total clicks/taps
- Total page transitions
- First-use completion time
- At least two repeat-run completion times and median
- Navigation efficiency and backtracking
- Context switches between modules
- Visibility of critical actions and information
- Decision clarity
- Errors, recovery steps, and confirmation feedback
- Keyboard-only path
- Mobile path

Compare with the previous milestone or previous workflow where available:

```text
Journey:
Previous clicks / current clicks:
Previous median time / current median time:
Page transitions before / after:
Context switches before / after:
Finding:
Improvement:
Retest result:
```

Remove unnecessary steps, repeated entry, lost filters, lost customer context, ambiguous actions, and
avoidable scrolling before closing the milestone. Preserve safety, authorization, explicit destructive
confirmation, and auditability.

## 9. Feature Parity Audit

For each implemented module, compare workflow maturity against the owner-approved AiSensy reference
without copying implementation or proprietary presentation.

Review for essential missing:

- Workflows and workflow stages
- Actions and shortcuts
- Search, filters, sorting, and saved views
- Analytics and operational information
- Bulk actions
- History, audit, and recovery paths
- Loading, empty, error, disabled, and permission states
- Responsive behavior
- Accessibility and keyboard operation
- Operator productivity and information hierarchy

Classify each difference as:

- In scope and essential for the current milestone
- Valid later roadmap work
- Explicitly excluded by product scope
- Reference-only behavior that must not be copied

Resolve essential in-scope gaps before closeout. Record any essential deferred capability in
`ROADMAP.md` with scope, dependency, acceptance criteria, and reason before closing the milestone.
Never inflate scope merely because a reference contains an excluded SaaS, ads, payment, commerce,
marketplace, signup, reseller, or multi-project feature.

## 10. Security Review

Every workflow-changing milestone must verify security at the UI, route, object, API, cache, and tenant
boundaries. Hiding an action in the UI is not authorization evidence.

Verify:

- RBAC permissions
- Tenant isolation
- Object-level authorization
- Route protection
- API authorization
- Hidden and disabled actions
- Deep links and bookmarked URLs
- URL/query/path manipulation
- Direct API access and replay
- Bulk-action authorization
- Stale sessions and stale cached data
- Sensitive information exposure

Mandatory attempts as applicable:

1. Authorized happy path
2. Unauthorized UI attempt
3. Direct protected URL attempt
4. Direct API read/mutation attempt
5. Object-ID substitution
6. Cross-tenant object attempt
7. Hidden/disabled action replay
8. Bulk request containing unauthorized objects
9. Bookmark after logout, role change, tenant change, or session expiry
10. Cache/back-navigation leakage check
11. Sensitive DOM, network, storage, error, log, export, and download inspection

Use identities including authorized operator, restricted operator, manager/supervisor, administrator,
signed-out user, different-tenant user, and stale/disabled session where relevant.

Record:

```text
Workflow:
Role:
Tenant:
Attempt:
Expected:
Actual:
HTTP/API result:
UI result:
Audit evidence:
Sensitive data exposed: Yes / No
Result: PASS / FAIL
Severity:
Screenshot/trace:
Retest:
```

No milestone can be `Production Ready` when the API permits a hidden action, another tenant's data can
be discovered or accessed, protected content flashes before denial, direct URLs bypass permissions,
stale cache leaks previous identity data, or sensitive information appears beyond the user's role.
Fix verified authorization and tenant-isolation defects immediately and rerun the affected matrix.

## 11. Business Workflow Review

Validate the complete business outcome, not only individual screens or endpoints.

Review:

- Approved roles, responsibilities, handoffs, and separation of duties
- Entry criteria, state transitions, exit criteria, and terminal states
- Business validations, eligibility rules, required evidence, and rejection reasons
- Assignment, reassignment, ownership, queues, SLAs, reminders, and escalation behavior
- Idempotency, retries, concurrency, duplicate submission, stale-version, and race handling
- Bulk operations and partial-failure behavior
- Audit trail, immutable history, timeline, notification, and reporting evidence
- Permission changes during an active workflow
- Refresh, reconnect, session expiry, and interrupted-action recovery
- Error messages, correction path, confirmation, and rollback/compensation where supported
- Cross-module context: Customer 360, Reactivation, KYC, Inbox, Tasks, Documents, Campaigns,
  Templates, Notifications, Analytics, and Settings as applicable
- Realistic data volume, long-running jobs, pagination, exports, and asynchronous completion

Every workflow must preserve source-domain authority. Do not create a parallel state machine,
duplicate task/reminder system, synthetic KPI authority, or local-only business truth. Confirm that
refresh and another authorized device observe the same persisted result.

Record unimplemented essential business behavior in `ROADMAP.md`; do not hide it behind polished UI.

## 12. Production Readiness

A milestone is `Production Ready` only when all applicable evidence below passes:

- Feature scope complete with no placeholder or fake behavior
- Repository tests, lint, typecheck, build, contracts, migrations, and dependency gates pass
- Desktop/mobile visual review passes
- Chrome, Edge, and Firefox review passes
- Accessibility and keyboard/screen-reader review passes
- Performance comparison passes or approved regressions are documented and mitigated
- Real operator journey and UX quality review pass
- Feature parity audit is complete and essential gaps are resolved or roadmapped
- Security, RBAC, tenant, route, object, API, cache, deep-link, and sensitive-data review pass
- Business workflow outcome, recovery, audit, and persistence review pass
- No unresolved Blocker or Major issue
- Governance files are synchronized with the actual commit and evidence
- Remote HEAD is verified
- Deployment configuration, migrations, workers, secrets, observability, rollback, and operational
  ownership are ready for the affected scope

Repository-only evidence cannot establish host/browser performance, final rendered quality, real
operator completion, or production deployment. When those gates cannot be executed, report the
milestone as `Implemented`, `Repository Validated`, or `Blocked`—never `Production Ready`.

`Released` requires successful production deployment plus post-deployment smoke, authorization,
observability, and rollback-readiness verification against the deployed commit.

## 13. Release Checklist

### Scope and baseline

- [ ] Latest approved Git HEAD and target branch verified
- [ ] Exactly one roadmap milestone selected
- [ ] Existing implementation, shared components, APIs, permissions, tests, dependencies, and risks reviewed
- [ ] In-scope acceptance criteria and evidence plan recorded
- [ ] No completed work is being recreated and no excluded reference feature is included

### Implementation

- [ ] Product workflow and architecture preserved or approved changes documented
- [ ] Shared components reused or extended
- [ ] Loading, empty, error, partial, disabled, permission, success, and recovery states implemented
- [ ] Responsive and keyboard behavior implemented
- [ ] Verified in-scope bugs fixed
- [ ] No temporary code, fake data, duplicate authority, or unrelated change remains

### Repository validation

- [ ] Applicable lint, formatting, typecheck, unit, integration, contract, migration, security, and build gates pass
- [ ] Generated contracts and migration history remain valid
- [ ] Dependency/security audit reviewed
- [ ] Changed-file boundary reviewed
- [ ] Performance bundle/chunk comparison recorded

### Host validation

- [ ] Actual desktop `1920 × 1080` screenshots captured
- [ ] Actual mobile approximately `390 px` screenshots captured
- [ ] Populated, loading, empty, error/partial, focus, and long-content states reviewed as applicable
- [ ] Chrome desktop/mobile validated
- [ ] Edge desktop/mobile validated
- [ ] Firefox desktop/mobile validated
- [ ] Keyboard and screen-reader review completed
- [ ] FCP, LCP, interaction responsiveness, CLS/render stability, bundle, and lazy chunks measured
- [ ] Primary operator journey measured and optimized
- [ ] Feature parity audit completed
- [ ] Security/permission matrix completed
- [ ] Business workflow outcome and recovery completed
- [ ] All Blocker and Major findings fixed and retested

### Governance and delivery

- [ ] `PROJECT_STATE.md` updated
- [ ] `MODULE_STATUS.md` updated
- [ ] `IMPLEMENTATION_TRACKER.md` updated
- [ ] `VALIDATION_RESULTS.md` updated
- [ ] `CHANGELOG.md` updated
- [ ] `ROADMAP.md` updated when status, sequencing, dependency, estimate, or essential gap changes
- [ ] Milestone status uses the permanent status model honestly
- [ ] One Conventional Commit created
- [ ] Approved branch pushed
- [ ] Remote HEAD equals the reported commit SHA
- [ ] Next milestone not started without owner approval

### Deployment and release

- [ ] Deployment target and approved commit identified
- [ ] Required migrations, workers, queues, schedules, environment variables, secrets, and storage verified
- [ ] Monitoring, logs, alerts, audit evidence, and rollback plan verified
- [ ] Production smoke and critical operator journey pass
- [ ] Production permissions and tenant isolation pass
- [ ] Deployment SHA verified
- [ ] Milestone marked `Released` only after successful deployment evidence

## Canonical future prompt

```text
Continue from latest Git HEAD.

Follow:

- REPOSITORY_RULES.md
- ENGINEERING_STANDARDS.md
- PROJECT_STATE.md
- ROADMAP.md

Implement exactly one roadmap milestone.

Do not bypass any mandatory acceptance gates.

Commit.

Push.

Verify remote HEAD.

Stop only after the milestone reaches the highest status supported by the available evidence.

If host-machine-only evidence (browser, screenshots, operator journey, performance, etc.) cannot be
completed in this environment, record the milestone honestly as:
- Implemented
- Repository Validated
or
- Blocked

Never claim "Production Ready" without all required evidence.
```
