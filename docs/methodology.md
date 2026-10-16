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


# Methodology (week 3: indicators, Gate 2, site)

## Two clocks (D032)

Every indicator is computed on the **award year** (the year of the award date, the headline, D015)
and on the **tender start year**. The release year is not used: its record counts follow when the
publisher loaded records. The window is 2018 to 2025 (`gate.toml`, D038); awards outside it or
without a year are counted in `evidence/indicators.md` and left out of every figure.

## Indicators (`sql/indicators/060_indicators.sql`)

| Indicator | Figure | Denominator | Needs |
|---|---|---|---|
| Awarded value | sum of `amount_eur`; headline leaves out processes flagged `inconsistent_amount` (D025); `all` and `flagged` are published beside it; also by buyer region | none | award amount |
| Single-bidder share | awards with `numberOfTenderers = 1` | awards with a published tenderer count | tenderer count (empty: refused, D016) |
| Supplier concentration | value held by the five largest suppliers (equal split among an award's suppliers, D021) | headline awarded value of the same year | award amount and a linked supplier |
| Procedure mix | share of headline value per procedure class | headline value of awards that carry a class | procedure code |

Concentration is published as a range: `point` counts each identifier as one entity; `merged_upper`
also merges supplier ids whose canonical name carries a legal form and is shared by several 11-digit
ids. The audit (D036) estimates the identifier splits an entity in about 7% of multi-id names; the
upper bound is what you get if every such name were one company.

Every row carries its n. Populatedness per indicator, clock and period is stored in
`ind_populatedness`. No entity is named on any page or in any evidence file.

## Procedure classes (D023, fixed before the first indicator run)

The class comes from the `COD:n` code in `procurementMethodDetails`; the mapping is
`labels/procedure_class.csv`, built from the 30 codes in `docs/recon5_output.md`. Codes are
assigned by what the Italian title says:

| Class | Codes |
|---|---|
| open_or_restricted | 1 open, 2 restricted, 5 competitive dialogue, 7 dynamic system, 22 restricted from notice, 30 simplified restricted, 36 innovation partnership, 38 competitive with negotiation |
| negotiated_with_notice | 3 negotiated with prior publication, 23 special sectors with call, 114 negotiated from notices |
| negotiated_without_notice | 4 without prior publication, 6 special sectors without call |
| below_threshold | 8 economy/cottimo fiduciario, 34 negotiated below threshold, 35 art. 16 urbanisation works |
| direct_award | 12, 24, 25 in-house, 26, 32, 37, 40 direct award variants |
| framework_call_off | 16 framework, 27 and 28 call-offs |
| other | 14 selective (art. 238), 15 negotiated (unspecified), 29 constitutional bodies, 33 reserved |

The classes were set after reading the code titles and their counts (`docs/recon5_output.md`), and
before any indicator was computed: a mapping chosen by reading titles, not outcomes.

## Gate 2 (`src/appalti/gate2.py`, D038)

Thresholds are those of `gate.toml` (D007), unchanged. How they are applied:

* **Period test.** A period passes if the share of its awards carrying the required field is at
  least `min_populatedness`.
* **Pair test.** Two consecutive years are comparable if both pass the period test and the
  populatedness differs by no more than `max_populatedness_spread` (read as an absolute difference),
  the ratio of award counts (later over earlier) lies within `volume_ratio_band`, and the
  composition drift is at most `max_composition_drift`.
* **Composition drift** is the total variation distance between the two years' CPV-division shares
  of awards (half the sum of absolute differences, between 0 and 1).
* **Isolated years (D040, post hoc).** A year that passes its own test but whose every comparison with
  a neighbouring year was refused is refused too: a figure no neighbour can be compared with would
  read as a level. A year with no neighbour in the data is judged on populatedness alone.
* Every judgement is a row in `gate_decision` with its measures, failed measures and the text that
  the site prints. Rows are appended, never rewritten; the site reads the latest run.
* A year that fails the period test (including the isolated-year rule) is not drawn; a pair that fails is not joined by a line and its
  reason is printed in its place.
* `informational.max_clock_divergence` triggers a note, not a refusal, when the two clocks disagree
  on awarded value by more than 25% (relative to the larger).

## Site (`src/appalti/site.py`)

Static HTML and inline SVG, no JavaScript and no external resource. Output has no timestamp, so
`git diff site/` shows exactly which published numbers changed between runs. Every page carries the
Gate 1 exclusion line (D031) and the list of what the figures do not mean. Charts carry a legend,
direct labels, native tooltips and a table view; the palette passes the validator, with the
contrast warning on three slots handled by those labels and tables.

## Pages publishes the committed `site/` (D039)

CI runs the whole pipeline on the 2025 file and fails if `gate_decision` is empty or no site is
built, but the site that goes live is the committed `site/`, built locally from the full file.

## Region `unknown` (D041)

About 7.5% of awards have no usable buyer postal code: the field holds a letter-and-dot placeholder
or a three-digit string. They are reported as region `unknown`, never guessed.
