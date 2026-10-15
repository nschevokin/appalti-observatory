# Day 1 reconnaissance

**Status: queries written, NOT yet run.**
Run date: _to fill_ · Input file: `data/raw/full.jsonl.gz` · sha256: _to fill_

## Decision rules (committed before running anything, 2026-10-15)

Commit this file, with this section and the `TBD` answers below, BEFORE running `make recon`.

- Identifier completeness above 90 percent: entity resolution is a join on identifier, with name matching only for the remainder. The headline becomes coverage and comparability.
- Between 70 and 90 percent: hybrid. Join where identifiers exist, match by name where they do not, report accuracy separately for both paths.
- Below 70 percent: entity resolution is the core, and the indicator set shrinks to two or three measures that can be supported properly.
- If `numberOfTenderers` is populated for fewer than half the tenders in any year, that year is excluded from the single-bidder indicator and the exclusion appears on the site.

Note on Q2, to settle in writing before running: the spec says "identifier completeness" without naming the population. The runner reports it overall and by role (buyer, supplier, tenderer). Decision made here, in advance: the branch is taken on **suppliers and buyers separately**; if they land in different bands, the lower band wins for the project's headline and the other is documented as a partial exception. _Edit nothing above this line after the first run; append instead._

## The eight measurements

Queries live in `sql/recon/recon.sql`. `make recon` writes the full output, with the SQL of each query, to `docs/recon_output.md`. Summarise here.

| # | Question | Answer | Query |
|---|----------|--------|-------|
| 0 | Does each line have the shape I assumed (top-level keys)? | TBD | `q0_structure` |
| 1 | Is `ocid` unique across lines? | TBD | `q1_ocid_unique` |
| 2 | Share of `parties[].identifier.id` populated, schemes present | TBD | `q2_identifier_*` |
| 3 | Real record counts per calendar year, by award date and tender date | TBD | `q3_year_counts` |
| 4 | Populatedness of `tender.numberOfTenderers` per year | TBD | `q4_tenderers_*` |
| 5 | `value.amount` nulls, negatives, non-EUR currencies | TBD | `q5_amounts_*` |
| 6 | Awards with a matching contract; does `contracts[].awardID` resolve | TBD | `q6_award_contract_*` |
| 7 | Do amendments restate a value or a delta | TBD | `q7_amendments_*` (needs eyeballing) |
| 8 | Distribution of `parties[].roles` | TBD | `q8_roles` |

## Branch resolved

_TBD: join / hybrid / entity-resolution-core, with the Q2 figure that decided it._

## Row counts vs the publisher's stated totals (ticket A3 feeds this)

Stated: 562,862 tenders, 324,030 awards, 185,259 contracts, 1,474,656 parties. Observed: _TBD_. Gap explained: _TBD_.
