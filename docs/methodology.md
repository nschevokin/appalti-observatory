# Methodology (week 2: entities and facts)

All numbers come from `evidence/`; this page says how they are made.

## Input and gates

Only records that passed Gate 1 (`clean_*` views, ticket A4) enter the warehouse. If Gate 1
aborted, `appalti resolve build` refuses to run. The input file is pinned by sha256 in
`manifest.json`.

## Entities (`sql/entities/040_entities.sql`)

* **Key.** The party's `identifier.id`, trimmed and upper-cased, with the scheme `IT-CF`.
  Digit-only ids shorter than 11 characters are zero-padded only when the padded form exists
  among the 11-digit supplier ids (D027). Anything else stays as published.
* **entity_id.** `E` plus the first 16 hex characters of the sha256 of the key: deterministic,
  so the same input always gives the same ids.
* **kind.** `buyer`, `supplier` or `both` (an id seen in both roles).
* **Canonical name.** The most frequent spelling that is not the id itself; ties go to the
  alphabetically first. The `method` column is `identifier`, `name_match` (only after an audit
  rule was applied) or `singleton`. `confidence` is NULL on purpose (D033).
* **Consortia.** Every supplier on an award is treated as its own entity; a grouping cannot be
  told apart from a multi-winner framework (D021).

## Facts (`sql/entities/050_facts.sql`)

* `fact_award`: one row per award. `amount_eur` is the award amount; `tender_amount` the tender's.
  `inconsistent_amount` is true when the awards of a process sum to more than 10 times its tender
  amount (D025). `award_date_flagged` marks award dates outside 2019-01-01 to the publication
  date (D014, D029). `single_bidder` is NULL everywhere because `numberOfTenderers` is empty (D016).
* `fact_award_supplier`: bridge, one row per award and distinct supplier, `share` = 1/n.
  Shares of an award add up to 1; awards without a supplier have no rows.
* **Region.** First two digits of the buyer's postal code, mapped through
  `labels/cap_region.csv` (93 prefixes, 20 regions); otherwise `unknown`. A prefix can cross a
  regional border, so some buyers are assigned to a neighbouring region. The error rate is measured
  on 50 postal codes (`appalti regions sample`, then `eval`) and published.

## Entity audit

The identifier join can split one real entity over several ids. The audit measures how often.

1. `appalti resolve sample` lists names with several 11-digit ids and a legal-form token, sorts
   each group into a stratum by rule (see D034) and draws a fixed-seed sample into
   `audit/groups_dev.csv` and `audit/groups_test.csv` (these contain names and ids of legal
   persons only, never natural persons).
2. Label each dev group `same`, `different`, `mixed` or `unsure`.
3. `appalti resolve eval` writes `evidence/audit_dev.md`: split rate with a 95% interval,
   precision per rule, and whether each rule meets the pre-registered bar.
4. A decision entry names the rules to apply (`apply_rules` in `audit.toml`); then
   `appalti resolve build` is rerun.
5. `appalti resolve confirm` opens the test split once and records the result in
   `evidence/audit_test_confirmation.json`.

What the audit cannot see: two ids for one entity under different names, and entities with a
single id and several real-world meanings.

## Privacy

Published reports show counts only. Names appear only for legal-form names with 11-digit ids
(D022); 16-character codes are never printed (D030). The audit sheets are local working files;
check them before uploading.
