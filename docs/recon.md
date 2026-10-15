# Day 1 reconnaissance

**Status: three passes run on 2026-10-15 (`recon.sql`, `recon2.sql`, `recon3.sql`); reconnaissance complete.**
Run date: 2026-10-15 · Input file: `data/raw/full.jsonl.gz` · sha256: 35266f3e1a5bfe5680207dd85ad18ad55858c9a2e8b7dc66447c94d5313ab720
Download URL used: `https://data.open-contracting.org/en/publication/117/download?name=full.jsonl.gz` (the spec wrote `data.opencontracting.org`, which does not resolve; the registry host is hyphenated).
Raw output with every query: `docs/recon_output.md`.

## Decision rules (committed before running anything, 2026-10-15)

Commit this file, with this section and the `TBD` answers below, BEFORE running `make recon`.

- Identifier completeness above 90 percent: entity resolution is a join on identifier, with name matching only for the remainder. The headline becomes coverage and comparability.
- Between 70 and 90 percent: hybrid. Join where identifiers exist, match by name where they do not, report accuracy separately for both paths.
- Below 70 percent: entity resolution is the core, and the indicator set shrinks to two or three measures that can be supported properly.
- If `numberOfTenderers` is populated for fewer than half the tenders in any year, that year is excluded from the single-bidder indicator and the exclusion appears on the site.

Note on Q2, to settle in writing before running: the spec says "identifier completeness" without naming the population. The runner reports it overall and by role (buyer, supplier, tenderer). Decision made here, in advance: the branch is taken on **suppliers and buyers separately**; if they land in different bands, the lower band wins for the project's headline and the other is documented as a partial exception. _Edit nothing above this line after the first run; append instead._

## The eight measurements (first pass, 2026-10-15)

| # | Question | Answer | Query |
|---|----------|--------|-------|
| 0 | Does each line have the assumed shape? | Yes. One process per line; top-level keys `ocid`, `tag`, `id`, `date`, `tender`, `language`, `initiationType`, `buyer`, `parties`, `awards`, `contracts`. 562,886 lines, of which 24 are stubs (only `ocid`, `tag`, `id`: no date, tender or initiationType). 562,862 lines carry a tender. | `q0_structure` |
| 1 | Is `ocid` unique? | Yes: 562,886 lines, 562,886 distinct. No deduplication needed. | `q1_ocid_unique` |
| 2 | Identifier completeness, schemes | 100% for buyers (557,762) and suppliers (355,681); one scheme, `IT-CF`. A third role, `payer` (561,213 rows), uses scheme `internal` with GUIDs, unusable for resolution. Overall 1,474,655 of 1,474,656. | `q2_identifier_by_role`, `q2_identifier_schemes` |
| 3 | Records per calendar year | Release date: 2020 41,126; 2021 226,138; 2022 14,067; 2023 141,632; 2024 130,494; 2025 9,405; 24 undated. Tender start: 2018 109,404; 2019 108,394; 2020 89,362; 2021 84,619; 2022 139,431; 2023 31,625; 2024 27. Award date: ≤2017 500 (back to 2000); 2018 58,680; 2019 48,495; 2020 55,781; 2021 51,474; 2022 85,658; 2023 22,504; 2024 671; 2025 45; 2027 2; undated 220. | `q3_year_counts` |
| 4 | `numberOfTenderers` populatedness | **0% in every year**, and null on all 562,862 tenders. | `q4_tenderers_by_year`, `q4_tenderers_values` |
| 5 | Amount nulls, negatives, currencies | Awards: 324,009 EUR, 21 with no currency. No negatives, no non-numeric values. Null amount 171 (150 EUR + 21 no currency), zero 321. Median 108,790. Ten largest: 1.78 bn to 34.5 bn. | `q5_amounts_award`, `q5_amounts_largest` |
| 6 | Awards vs contracts | 324,030 awards; 185,259 contracts; 185,252 awards have a contract (57.2%). One contract per award (no duplicated award ids). 1 contract with null `awardID`, 6 dangling. Share of awards with a contract by award year: 2018 55.3%, 2019 57.4%, 2020 55.2%, 2021 62.3%, 2022 58.7%, 2023 50.0%, 2024 24.3%, 2025 17.8%. | `q6_award_contract_link`, `q6_contract_share_by_award_year` |
| 7 | Amendments: restated value or delta? | Neither. All 26,807 sit at contract level and carry only `id`, `date` and an optional `rationale` (24,917 of them). No value, no change list. Summing award values cannot double count through amendments, and revised values are not visible. | `q7_*` |
| 8 | Role distribution | Every party carries exactly one role: payer 561,213; buyer 557,762; supplier 355,681. No `tenderer` role exists. | `q8_roles` |

## Branch resolved

**Join.** Buyers 100% and suppliers 100% are both above the 90% threshold set before the run. Completeness is not correctness: the second pass checks id format, id-to-name consistency and consortium encoding before D019 is confirmed.

## Findings that contradict the spec

1. **Single-bidder cannot be computed.** `numberOfTenderers` is empty everywhere. By the pre-registered rule every year is excluded. See D016, D018.
2. **The stated period is a release-date window.** "January 2020 to September 2025" describes release dates. Award dates run mostly 2018 to 2023, with 500 awards before 2018, 2 dated 2027, and 220 undated. Applied to award dates, the spec's Gate 1 rule (date between 2019-01-01 and publication) would reject about 18% of awards and trigger the 2% abort. See D014.
3. **The clock decides what the gate allows.** Release-date years fail the [0.5, 2.0] volume band on almost every adjacent pair (2021/2020 5.50; 2022/2021 0.06; 2023/2022 10.07). Award-date years 2018 to 2022 pass (steps 0.83, 1.15, 0.92, 1.66); 2023/2022 is 0.26 and fails. The choice of clock was made after seeing this, so it is recorded as a post-hoc decision (D015); the thresholds were not changed.
4. **Heavy tail in award values.** The ten largest awards are between 1.78 and 34.5 billion EUR against a median of 108,790. An outlier rule is needed before any total is published (D017).

## Row counts vs the publisher's stated totals

| Object | Stated | Observed |
|---|---|---|
| Tenders | 562,862 | 562,862 (lines with a tender; plus 24 stub lines) |
| Awards | 324,030 | 324,030 |
| Contracts | 185,259 | 185,259 |
| Amendments | 26,807 | 26,807 |
| Parties | 1,474,656 | 1,474,656 |
| Suppliers | 390,526 | 355,681 supplier-role parties; gap unexplained, see `q14_supplier_count_gap` |
| Milestones | 83,587 | not yet checked |

The stated figure of about 1,500 releases without an OCID cannot be checked from the file, since those releases are excluded from the downloads.

## Second pass (ticket A1b), run 2026-10-15

`sql/recon/recon2.sql`, `make recon2`, output in `docs/recon2_output.md`. Written after the first pass, so not part of the pre-registered rules.

**Identifiers (suppliers, 355,681 party rows, 78,987 distinct ids).** 92.7% of rows carry an 11-digit id; 6.4% a 16-character fiscal code (natural persons: 22,668 rows, 15,217 distinct ids, 19.3% of distinct supplier ids); 0.8% other formats (lengths 1 to 20); 0.2% digit-only ids shorter than 11 (750 rows, 530 ids), possibly with lost leading zeros. Buyers: 19,365 distinct ids; 552,763 rows 11-digit, 4,979 rows of length 14 (538 ids), 20 rows 16-character. 828 ids appear as both buyer and supplier.

**One id, many spellings.** 63.3% of supplier rows belong to an id with two or more name spellings; 675 ids have six or more (up to 35 for one id). The spellings include legal-form variants, renamings after mergers (two different corporate names under one id), and a name field that just repeats the id. The identifier is doing the work that name matching would otherwise do.

**One name, many ids.** 3,221 of 99,226 distinct supplier names (3.3%) map to two or more ids, covering 16.8% of supplier rows. Homonyms, branches or split entities: not distinguishable from counts alone.

**Consortia (D006).** Names carrying a consortium or grouping marker: consorzio 6,253 rows (830 ids), RTI/ATI 259 (142 ids), raggruppamento 29, GEIE/rete 15; together 1.8% of supplier rows. 30,154 awards (9.3%) list two or more suppliers, up to 49; 293,006 have exactly one; 870 have none. Members therefore appear as separate suppliers on the award; a temporary grouping cannot be told apart from a multi-winner framework.

**Value.** Total award value is about 358 billion EUR (before any outlier rule). 232 awards of 100 million or more (0.07% of awards) hold 42% of it: 22 awards of 1 billion or more hold 29%. Contracts carry no value at all (0 of 185,259). For the ten largest awards, three have an award value equal or close to their own tender's value; seven exceed their tender value by 3.5 to about 1,000 times, one by almost exactly 1,000x. That pattern points to unit or decimal errors, not to genuine awards.

**Supplier count gap.** Resolved. The spec's 390,526 equals the number of award-supplier references (the sum of the `suppliers` array lengths over all awards); distinct supplier party rows are 355,681.

**Procedure and slicing fields.** `procurementMethod` is empty on all 562,862 tenders. The procedure sits in `procurementMethodDetails` as `COD:n ; TITLE:...`: direct award 30.3%, call-off from a framework 29.7%, negotiated below threshold 12.0%, negotiated without notice 10.3%, open procedure 7.7%. CPV is present (scheme CPV on all 698,350 items; classification on 99.98% of tenders), so a CPV division is derivable. The region probe returned 0%, but it queried `address.region`, a field that may not exist; addresses exist on 1,118,220 parties. `additionalIdentifiers` appears on 557,815 parties, close to the number of buyer rows (557,762); scheme unknown, to be checked in the third pass.

## Third pass (ticket A1c), run 2026-10-15

`sql/recon/recon3.sql`, `make recon3`, output in `docs/recon3_output.md`. Written after the first two passes, so not part of the pre-registered rules.

**Award value against its tender's value** (274,240 processes with awards; the total of 358.1 billion EUR reconciles with the earlier bucket table):

| Sum of awards vs tender amount | Processes | Awarded EUR |
|---|---|---|
| at or below tender | 267,722 | 253.6 bn |
| up to 1.5x | 5,721 | 11.5 bn |
| 1.5x to 2x | 327 | 1.6 bn |
| 2x to 10x | 212 | 3.4 bn |
| 10x to 100x | 61 | 11.2 bn |
| over 100x | 33 | 76.7 bn |
| no usable tender amount | 25 | 0.2 bn |
| no award amount | 139 | none |

97.6% of processes sit at or below their tender amount and 99.7% within 1.5x. The 94 processes above 10x (0.034% of processes) hold 87.8 billion EUR, 24.5% of all awarded value.

**Identifiers.** Of 530 digit-only supplier ids shorter than 11, only 22 have a zero-padded 11-digit counterpart among the supplier ids.

**Buyer addresses.** `postalCode`, `locality` and `countryName` are present on all 557,762 buyer rows (`streetAddress` on 557,759). There is **no region or province field**, so the 0% in `q17` was a real absence, not a bad probe. Region has to be derived.

**Buyer additional identifiers.** Scheme `AUSA` on all 557,762 buyer rows, one per row (the contracting-authority register code, separate from the fiscal code).

**Value by number of suppliers on the award.** One supplier: 72.6% of value; two to five: 19.4%; six or more: 7.9%; none: 0.2%. So 27.2% of awarded value sits on awards with several suppliers, which is the part the equal split in D021 touches.

**Procedure mix by tender start year** (share of tenders; direct award, call-off from a framework, negotiated below threshold, negotiated without notice, open, other):

| Year | Tenders | Direct | Call-off | Neg. below | Neg. no notice | Open | Other |
|---|---|---|---|---|---|---|---|
| 2018 | 109,404 | 16.2 | 33.3 | 0.0 | 17.6 | 8.5 | 24.3 |
| 2019 | 108,394 | 21.7 | 28.4 | 13.3 | 13.8 | 9.8 | 12.9 |
| 2020 | 89,362 | 20.8 | 37.0 | 17.8 | 10.6 | 8.1 | 5.9 |
| 2021 | 84,619 | 42.3 | 23.1 | 16.6 | 6.0 | 7.1 | 4.9 |
| 2022 | 139,431 | 40.1 | 29.3 | 14.2 | 5.6 | 6.7 | 4.1 |
| 2023 | 31,625 | 60.0 | 20.8 | 9.6 | 3.6 | 3.4 | 2.5 |

30 distinct codes; no tender lacks the details field. The mix moves a lot: direct awards go from 16% to 60%, and the code for negotiated procedures below threshold does not appear at all in 2018 while "other" is 24%, so the coding regime appears to change between 2018 and 2019. As an indication only (not the gate computation), half the summed absolute difference between adjacent years is about 20% (2018 to 2019), 13%, 22%, 6% and 20% (2022 to 2023) against the 0.15 band in `gate.toml`. Whether the shifts are real policy effects, coding changes, or publication lag in the thin 2023 cohort cannot be told from these counts.

## Open items for `docs/methodology.md`

1. Define `composition_drift` precisely (proposal: half the summed absolute difference in CPV-division shares between adjacent periods, by award count) before the first indicator run.
2. Procedure mix: the code-to-class mapping (D023) must be versioned by year, and 2018 needs a decision (publish with a coding caveat, or start at 2019).
3. Large awards that equal their own tender value (for example 7.3 and 4.5 billion EUR) are internally consistent and stay in; framework ceilings are not spending, so the site must not read them as such.
4. `AUSA` is kept as a buyer attribute; check later whether one fiscal code carries several AUSA codes.
5. Award clock (D015) and tender clock disagree on the 2023 tail; the gate is run on the award clock.

## Status

Reconnaissance (A1) is complete after three passes. Next: A2 (download with a sha256 manifest), A3 (staging, with row counts reconciled against the table above), A4 (validation gate).
