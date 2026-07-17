# FR-CAM-11 (Cost Engine) — Specification Gap Analysis

> **Status:** Blocking. Phase 6 Step 5 implementation is **stopped** pending amendment of the frozen
> design documents. This note documents the gap only; it proposes no implementation.
>
> **Requirement under analysis:** FR-CAM-11 — *"Cost calculator: pre-send estimated spend from the
> rate card (by category/country)"* (Doc 01 §FR, priority **M**, Phase 6).
>
> **Agreed scope once specs are amended** (recorded here so the amendment can target it): pre-send
> **estimation only** — populate `campaigns.estimated_cost` and serve
> `POST /campaigns/{uuid}/estimate-cost`. `pricing_model`, `is_billable`, `messages.cost_*` and
> `campaigns.actual_cost` are explicitly **out of scope** until a specification defines their rules.

---

## 1. Missing entities

| # | Missing | Evidence |
|---|---|---|
| E1 | **Rate Card.** Doc 01 FR-CAM-11, Doc 04 §17 and Doc 04 §31 all reference *"the rate card"* as an existing authority. Doc 03 defines **no such entity** — it appears in no `CREATE TABLE` and in no entity/domain mapping table. | Doc 03 (49 tables, none is a rate card) |
| E2 | **Rate-card versioning / effective dating.** Meta's published rates change over time. Nothing owns "which rate applied when", so an estimate is not reproducible after a rate change, and estimate-time vs send-time rate selection is undefined. | absent from Doc 03 |
| E3 | **Pricing-data provenance.** No entity records the card's source, import date, or authority. Doc 12 §53 places Meta pricing **outside** the frozen docs, so no internal entity imports or owns it. | Doc 12 §53 |

## 2. Missing schema

- **No rate-card table.** Undefined: table name, primary key, uniqueness (presumably over
  `(country, category[, effective_from])`), indexes for the lookup, and nullability.
- **Unit-price column undefined.** No declared precision/scale for a unit rate. Consumers are
  inconsistent in scale: `campaigns.estimated_cost DECIMAL(14,4)` vs
  `campaign_recipients.cost_amount DECIMAL(12,6)` and `messages.cost_amount DECIMAL(12,6)`.
- **Rounding rule undefined.** `unit(6dp) × count → total(4dp)` requires a stated rule (round vs
  truncate; per-recipient, per-`(country,category)` group, or per-campaign). Different choices give
  different totals at 250k recipients — the exact figure FR-CAM-11 calls the headline number.
- **Currency storage undefined.** `campaigns.cost_currency CHAR(3) NULL` and
  `messages.cost_currency CHAR(3) NULL` exist, but nothing states whether the card is
  single-currency (USD, per Doc 04's sample) or multi-currency, nor where the currency is authored.
- **Consumer columns already frozen** (these exist and are *not* part of the gap):
  `campaigns.estimated_cost`, `campaigns.actual_cost`, `campaigns.cost_currency`,
  `campaign_recipients.cost_amount`, `messages.{pricing_model,is_billable,cost_amount,cost_currency}`.

## 3. Missing relationships

| # | Relationship | What is undefined |
|---|---|---|
| R1 | Rate card ↔ **organization** | Global (one Meta card) or per-org? Doc 04 §17 says *"No reseller markup"*, implying global; but every cost column is on a per-org row, and `cost_currency` is per campaign. Tenancy and currency ownership unresolved. |
| R2 | Rate card ↔ **country** | The dimension is `contacts.country_code CHAR(2) **NULL**`. Behaviour for a NULL country is undefined (skip / 422 / default / derive from `wa_id` E.164 prefix). No derivation rule exists in Doc 03. |
| R3 | Rate card ↔ **category** | `message_templates.category` (3 values) is the only category a campaign can carry. The join is never declared. |
| R4 | Rate card ↔ **currency / FX** | No FX entity. If the card is multi-currency, how a single `estimated_total` is produced is undefined. |
| R5 | Estimate ↔ **roster** | Undefined whether the estimate counts all audience matches or only sendable recipients. The roster already excludes opt-outs (`audience_ref_json._excluded_opted_out`, Doc 03 §8.1), so the two differ. |

## 4. Missing API contracts

`POST /campaigns/{uuid}/estimate-cost` (Doc 04 §17, `campaigns:read`, rate class `read`, `422`)
is specified **only by a sample response**. Undefined:

- **Request body** — none, or overrides (audience/template/date)?
- **Error contract** — the route table lists a bare `422` with **no machine `code`**, unlike its
  siblings (`/send` names `recipients_not_opted_in`, `template_not_approved`,
  `messaging_limit_exceeded`). No code exists for *rate card not configured*, *unknown
  country/category*, or *NULL country*.
- **Empty-card behaviour** — the required outcome when no rate row matches is unstated.
- **`notes[]`** — the sample emits a free-text note; its source, vocabulary and trigger conditions
  are undefined.
- **Persistence** — whether the endpoint writes `campaigns.estimated_cost` or is purely a read.
- **Second consumer.** Doc 04 §31 (`/messages/bulk/estimate`) states it *"returns the same
  rate-card breakdown as campaign estimation (§17)"*, and Doc 05 §872 (wizard step 6) renders the
  same breakdown. The rate card is therefore a **shared** contract, but no shared contract is
  specified — only a cross-reference to a sample.

## 5. Missing pricing semantics

- **`pricing_model` (PMP/CBP)** — Doc 03 §9.2 names the values *("per-message vs legacy")* but no
  document states the **determination rule**.
- **`is_billable`** — column frozen (`NOT NULL DEFAULT 0`); no rule defines when a message is
  billable.
- **Free tier** — Doc 04 §17's sample note references *"Free-tier service conversations"*. The free
  tier is never defined: no quota, no reset period, no effect on an estimate.
- **Rate selection in time** — estimate-time vs send-time card, and behaviour across a rate change
  mid-campaign.
- **Rounding, precision, currency conversion** — see §2.
- **Actual cost** — no source is defined. Meta's webhook `pricing` payload is **not specified in
  Doc 07** (Doc 07 contains no pricing content whatsoever), and Doc 12 §53 places it outside the
  frozen set. *(Out of agreed scope for this milestone; recorded because the contract is absent.)*

## 6. Contradictions with the frozen documents

1. **`service` category is unreachable yet referenced by the cost engine.**
   `messages.category` permits `marketing/utility/authentication/**service**` (Doc 03 §9.2 line 958,
   annotated *"(billing)"*), but `ck_tpl_category` permits only
   `marketing/utility/authentication` (Doc 03 §7.1 line 682). A campaign always sends a template, so
   `service` can never arise from a campaign — yet Doc 04 §17's estimate-cost sample explicitly
   emits a note about **service** conversations. The estimate references a category its own input
   domain cannot produce.

2. **The rate card is treated as internal authority but declared external.**
   Doc 01 FR-CAM-11 and Doc 04 §17 compute from *"Meta's real rate card"* as though it were an owned
   internal source with a queryable shape. Doc 12 §53 lists Meta pricing under **"External
   (referenced by the frozen docs, not restated here)"**. The frozen set therefore depends on a
   source it neither defines, imports, nor assigns an owner — the direct cause of gaps §1–§5.

3. **Global card vs per-tenant currency.**
   Doc 04 §17 asserts *"No reseller markup"* (one true Meta card ⇒ global), while Doc 03 carries
   `cost_currency` per campaign and per message (⇒ per-tenant currency). Both cannot hold without a
   stated FX or tenancy rule; neither is stated. (See R1/R4.)

4. **Precision mismatch across the cost chain.**
   Per-message costs are `DECIMAL(12,6)`; campaign totals are `DECIMAL(14,4)`. The frozen schema
   defines both endpoints of the chain but no rule for crossing between them. (See §2.)

---

## Required to unblock

Amendment of the frozen specification to define: the rate-card **entity + schema** (Doc 03), its
**relationships** (org/country/category/currency, incl. NULL `country_code`), the
**estimate-cost request/error contract** including a machine code for an unconfigured card
(Doc 04 §17, and §31's shared breakdown), and the **rounding/precision/currency** rules.

Implementation resumes from the amended, re-frozen specification. Per the agreed scope above, the
amendment need not define `pricing_model`, `is_billable`, or actual-cost semantics to unblock
**estimation**; those remain deferred to the milestone that specifies them.
