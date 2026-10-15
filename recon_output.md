# Recon output
Run date: 2026-10-15T16:27:20
Input: `data/raw/full.jsonl.gz`
DuckDB: 1.5.6

## q0_structure
```sql
-- Top-level keys and how often each is present.
SELECT k AS top_level_key, count(*) AS n,
       round(100.0 * count(*) / (SELECT count(*) FROM raw), 2) AS pct_of_lines
FROM (SELECT unnest(json_keys(doc)) AS k FROM raw)
GROUP BY k ORDER BY n DESC;
```
| top_level_key | n | pct_of_lines |
|---|---|---|
| ocid | 562886 | 100.0 |
| tag | 562886 | 100.0 |
| id | 562886 | 100.0 |
| date | 562862 | 100.0 |
| tender | 562862 | 100.0 |
| language | 562862 | 100.0 |
| initiationType | 562862 | 100.0 |
| buyer | 562860 | 100.0 |
| parties | 562157 | 99.87 |
| awards | 274240 | 48.72 |
| contracts | 173656 | 30.85 |

## q1_ocid_unique
```sql
SELECT count(*) AS lines,
       count(doc->>'$.ocid') AS with_ocid,
       count(DISTINCT doc->>'$.ocid') AS distinct_ocid,
       count(*) - count(DISTINCT doc->>'$.ocid') AS surplus_lines
FROM raw;
```
| lines | with_ocid | distinct_ocid | surplus_lines |
|---|---|---|---|
| 562886 | 562886 | 562886 | 0 |

## q1_ocid_duplicates_top
```sql
SELECT doc->>'$.ocid' AS ocid, count(*) AS lines
FROM raw GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC LIMIT 10;
```
| ocid | lines |
|---|---|

## q2_identifier_by_role
```sql
-- Populated identifier.id overall and by role.
WITH p AS (
  SELECT nullif(trim(party->>'$.identifier.id'), '') AS id,
         coalesce(from_json(party->'$.roles', '["VARCHAR"]'), []::VARCHAR[]) AS roles
  FROM r_party)
SELECT 'ALL' AS role, count(*) AS n, count(id) AS with_id,
       round(100.0 * count(id) / count(*), 2) AS pct_with_id FROM p
UNION ALL
SELECT r, count(*), count(id), round(100.0 * count(id) / count(*), 2)
FROM (SELECT unnest(roles) AS r, id FROM p) GROUP BY r
ORDER BY n DESC;
```
| role | n | with_id | pct_with_id |
|---|---|---|---|
| ALL | 1474656 | 1474655 | 100.0 |
| payer | 561213 | 561212 | 100.0 |
| buyer | 557762 | 557762 | 100.0 |
| supplier | 355681 | 355681 | 100.0 |

## q2_identifier_schemes
```sql
SELECT coalesce(party->>'$.identifier.scheme', '<null>') AS scheme,
       count(*) AS n,
       count(nullif(trim(party->>'$.identifier.id'), '')) AS with_id
FROM r_party GROUP BY 1 ORDER BY n DESC LIMIT 30;
```
| scheme | n | with_id |
|---|---|---|
| IT-CF | 913443 | 913443 |
| internal | 561213 | 561212 |

## q2_identifier_samples
```sql
-- Eyeball the id format per scheme (is it a fiscal code, a VAT number, junk?).
SELECT scheme, id FROM (
  SELECT party->>'$.identifier.scheme' AS scheme,
         party->>'$.identifier.id' AS id,
         row_number() OVER (PARTITION BY party->>'$.identifier.scheme' ORDER BY random()) AS rn
  FROM r_party WHERE nullif(trim(party->>'$.identifier.id'), '') IS NOT NULL)
WHERE rn <= 5 ORDER BY scheme;
```
| scheme | id |
|---|---|
| IT-CF | 10711191006 |
| IT-CF | 02191980420 |
| IT-CF | 00175660554 |
| IT-CF | 05865511009 |
| IT-CF | 00624560231 |
| internal | B7C9EC5C-E419-4418-9EBC-8090DE6EAB08 |
| internal | CD750B41-F74B-45F0-9ECF-E81CFD52EB06 |
| internal | 0102350E-CD26-4C43-A75C-47AB6269907A |
| internal | 76D76BF1-5BFE-489F-B689-E001B0D23579 |
| internal | 28861D94-0888-46C5-BE17-588910ACBBF1 |

## q3_year_counts
```sql
-- Real counts per calendar year on three different clocks.
SELECT 'process_by_tender_period_start' AS basis, yr(doc->>'$.tender.tenderPeriod.startDate') AS year, count(*) AS n
FROM raw GROUP BY 2
UNION ALL
SELECT 'process_by_release_date', yr(doc->>'$.date'), count(*) FROM raw GROUP BY 2
UNION ALL
SELECT 'award_by_award_date', yr(award->>'$.date'), count(*) FROM r_award GROUP BY 2
ORDER BY basis, year;
```
| basis | year | n |
|---|---|---|
| award_by_award_date | 2000 | 1 |
| award_by_award_date | 2001 | 1 |
| award_by_award_date | 2002 | 2 |
| award_by_award_date | 2003 | 1 |
| award_by_award_date | 2008 | 3 |
| award_by_award_date | 2009 | 2 |
| award_by_award_date | 2010 | 5 |
| award_by_award_date | 2011 | 4 |
| award_by_award_date | 2012 | 2 |
| award_by_award_date | 2013 | 4 |
| award_by_award_date | 2014 | 8 |
| award_by_award_date | 2015 | 26 |
| award_by_award_date | 2016 | 61 |
| award_by_award_date | 2017 | 380 |
| award_by_award_date | 2018 | 58680 |
| award_by_award_date | 2019 | 48495 |
| award_by_award_date | 2020 | 55781 |
| award_by_award_date | 2021 | 51474 |
| award_by_award_date | 2022 | 85658 |
| award_by_award_date | 2023 | 22504 |
| award_by_award_date | 2024 | 671 |
| award_by_award_date | 2025 | 45 |
| award_by_award_date | 2027 | 2 |
| award_by_award_date | None | 220 |
| process_by_release_date | 2020 | 41126 |
| process_by_release_date | 2021 | 226138 |
| process_by_release_date | 2022 | 14067 |
| process_by_release_date | 2023 | 141632 |
| process_by_release_date | 2024 | 130494 |
| process_by_release_date | 2025 | 9405 |
| process_by_release_date | None | 24 |
| process_by_tender_period_start | 2018 | 109404 |
| process_by_tender_period_start | 2019 | 108394 |
| process_by_tender_period_start | 2020 | 89362 |
| process_by_tender_period_start | 2021 | 84619 |
| process_by_tender_period_start | 2022 | 139431 |
| process_by_tender_period_start | 2023 | 31625 |
| process_by_tender_period_start | 2024 | 27 |
| process_by_tender_period_start | None | 24 |

## q4_tenderers_by_year
```sql
-- Per-year populatedness of tender.numberOfTenderers (year = tender start, else release date).
SELECT coalesce(yr(doc->>'$.tender.tenderPeriod.startDate'), yr(doc->>'$.date')) AS year,
       count(*) AS tenders,
       count(doc->>'$.tender.numberOfTenderers') AS with_n_tenderers,
       round(100.0 * count(doc->>'$.tender.numberOfTenderers') / count(*), 2) AS pct_populated
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY 1;
```
| year | tenders | with_n_tenderers | pct_populated |
|---|---|---|---|
| 2018 | 109404 | 0 | 0.0 |
| 2019 | 108394 | 0 | 0.0 |
| 2020 | 89362 | 0 | 0.0 |
| 2021 | 84619 | 0 | 0.0 |
| 2022 | 139431 | 0 | 0.0 |
| 2023 | 31625 | 0 | 0.0 |
| 2024 | 27 | 0 | 0.0 |

## q4_tenderers_values
```sql
SELECT doc->>'$.tender.numberOfTenderers' AS n_tenderers, count(*) AS n
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY n DESC LIMIT 15;
```
| n_tenderers | n |
|---|---|
| None | 562862 |

## q5_amounts_award
```sql
SELECT coalesce(award->>'$.value.currency', '<null>') AS currency,
       count(*) AS awards,
       count(*) FILTER (WHERE (award->>'$.value.amount') IS NULL) AS null_amount,
       count(award->>'$.value.amount') - count(try_cast(award->>'$.value.amount' AS DOUBLE)) AS non_numeric,
       count(*) FILTER (WHERE try_cast(award->>'$.value.amount' AS DOUBLE) < 0) AS negative,
       count(*) FILTER (WHERE try_cast(award->>'$.value.amount' AS DOUBLE) = 0) AS zero,
       round(median(try_cast(award->>'$.value.amount' AS DOUBLE)), 0) AS median_amount,
       round(max(try_cast(award->>'$.value.amount' AS DOUBLE)), 0) AS max_amount
FROM r_award GROUP BY 1 ORDER BY awards DESC;
```
| currency | awards | null_amount | non_numeric | negative | zero | median_amount | max_amount |
|---|---|---|---|---|---|---|---|
| EUR | 324009 | 150 | 0 | 0 | 321 | 108790.0 | 34511040040.0 |
| <null> | 21 | 21 | 0 | 0 | 0 | None | None |

## q5_amounts_largest
```sql
-- Outliers: the ten largest award amounts (typos, cents-as-euro, framework ceilings).
SELECT ocid, award->>'$.id' AS award_id, award->>'$.value.currency' AS currency,
       try_cast(award->>'$.value.amount' AS DOUBLE) AS amount
FROM r_award ORDER BY amount DESC NULLS LAST LIMIT 10;
```
| ocid | award_id | currency | amount |
|---|---|---|---|
| ocds-hu01ve-8682745 | 2271439 | EUR | 34511040040.0 |
| ocds-hu01ve-8206857 | 2411006 | EUR | 25892844080.72 |
| ocds-hu01ve-7176845 | 1623125 | EUR | 7327602077.0 |
| ocds-hu01ve-8664938 | 2464958 | EUR | 4525000000.0 |
| ocds-hu01ve-8586450 | 2371559 | EUR | 3670799284.13 |
| ocds-hu01ve-8581608 | 2346956 | EUR | 3292999800.0 |
| ocds-hu01ve-7483943 | 1899387 | EUR | 2775000000.0 |
| ocds-hu01ve-8422821 | 2339934 | EUR | 2563675000.0 |
| ocds-hu01ve-7158806 | 1727142 | EUR | 2260000000.0 |
| ocds-hu01ve-7635795 | 2489785 | EUR | 1777361442.5 |

## q6_award_contract_link
```sql
WITH a AS (SELECT ocid, award->>'$.id' AS award_id FROM r_award),
     c AS (SELECT ocid, contract->>'$.id' AS contract_id, contract->>'$.awardID' AS award_id FROM r_contract)
SELECT (SELECT count(*) FROM a) AS awards,
       (SELECT count(*) FROM c) AS contracts,
       (SELECT count(*) FROM c WHERE award_id IS NULL) AS contracts_null_awardid,
       (SELECT count(*) FROM c WHERE award_id IS NOT NULL AND NOT EXISTS
          (SELECT 1 FROM a WHERE a.ocid = c.ocid AND a.award_id = c.award_id)) AS contracts_dangling_awardid,
       (SELECT count(*) FROM a WHERE EXISTS
          (SELECT 1 FROM c WHERE c.ocid = a.ocid AND c.award_id = a.award_id)) AS awards_with_contract,
       (SELECT count(*) FROM (SELECT ocid, award_id FROM a GROUP BY ALL HAVING count(*) > 1)) AS duplicated_award_ids;
```
| awards | contracts | contracts_null_awardid | contracts_dangling_awardid | awards_with_contract | duplicated_award_ids |
|---|---|---|---|---|---|
| 324030 | 185259 | 1 | 6 | 185252 | 0 |

## q6_contract_share_by_award_year
```sql
-- Is the contract stage published selectively over time?
WITH a AS (SELECT ocid, award->>'$.id' AS award_id, yr(award->>'$.date') AS year FROM r_award),
     c AS (SELECT ocid, contract->>'$.awardID' AS award_id FROM r_contract)
SELECT year, count(*) AS awards,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM c WHERE c.ocid = a.ocid AND c.award_id = a.award_id)) AS with_contract,
       round(100.0 * count(*) FILTER (WHERE EXISTS (SELECT 1 FROM c WHERE c.ocid = a.ocid AND c.award_id = a.award_id)) / count(*), 2) AS pct_with_contract
FROM a GROUP BY year ORDER BY year;
```
| year | awards | with_contract | pct_with_contract |
|---|---|---|---|
| 2000 | 1 | 0 | 0.0 |
| 2001 | 1 | 1 | 100.0 |
| 2002 | 2 | 2 | 100.0 |
| 2003 | 1 | 0 | 0.0 |
| 2008 | 3 | 3 | 100.0 |
| 2009 | 2 | 1 | 50.0 |
| 2010 | 5 | 2 | 40.0 |
| 2011 | 4 | 3 | 75.0 |
| 2012 | 2 | 2 | 100.0 |
| 2013 | 4 | 4 | 100.0 |
| 2014 | 8 | 6 | 75.0 |
| 2015 | 26 | 21 | 80.77 |
| 2016 | 61 | 42 | 68.85 |
| 2017 | 380 | 176 | 46.32 |
| 2018 | 58680 | 32445 | 55.29 |
| 2019 | 48495 | 27818 | 57.36 |
| 2020 | 55781 | 30785 | 55.19 |
| 2021 | 51474 | 32082 | 62.33 |
| 2022 | 85658 | 50283 | 58.7 |
| 2023 | 22504 | 11257 | 50.02 |
| 2024 | 671 | 163 | 24.29 |
| 2025 | 45 | 8 | 17.78 |
| 2027 | 2 | 0 | 0.0 |
| None | 220 | 148 | 67.27 |

## q7_amendments_where
```sql
-- Where do amendments live? (tender / awards / contracts level)
SELECT 'tender' AS level, coalesce(sum(json_array_length(doc->'$.tender.amendments')), 0) AS amendments FROM raw
UNION ALL SELECT 'award', coalesce(sum(json_array_length(award->'$.amendments')), 0) FROM r_award
UNION ALL SELECT 'contract', coalesce(sum(json_array_length(contract->'$.amendments')), 0) FROM r_contract;
```
| level | amendments |
|---|---|
| tender | 0 |
| award | 0 |
| contract | 26807 |

## q7_amendment_keys
```sql
SELECT k AS amendment_key, count(*) AS n
FROM (SELECT unnest(json_keys(am)) AS k
      FROM (SELECT unnest(from_json(contract->'$.amendments', '["JSON"]')) AS am FROM r_contract))
GROUP BY k ORDER BY n DESC;
```
| amendment_key | n |
|---|---|
| id | 26807 |
| date | 26807 |
| rationale | 24917 |

## q7_amendment_samples
```sql
-- READ THESE BY EYE: does an amendment carry a restated value or only a delta/change list?
SELECT ocid, contract->>'$.value.amount' AS contract_value, contract->'$.amendments' AS amendments
FROM r_contract WHERE json_array_length(contract->'$.amendments') > 0
LIMIT 15;
```
| ocid | contract_value | amendments |
|---|---|---|
| ocds-hu01ve-6935297 | None | [{"id":"200545","date":"2019-02-27T12:00:00Z"}] |
| ocds-hu01ve-6935379 | None | [{"id":"186577","date":"2018-07-25T12:00:00Z"}] |
| ocds-hu01ve-6935694 | None | [{"id":"238997","date":"2020-03-02T12:00:00Z","rationale":"ALTRE CAUSE IMPREVISTE ED IMPREVEDIBILI"},{"id":"238993","date":"2019-10-20T12:00:00Z","rationale":"MODIFICHE PREVISTE DAI DOCUMENTI DI GARA INIZIALI"}] |
| ocds-hu01ve-6935803 | None | [{"id":"195570","date":"2018-12-21T12:00:00Z","rationale":"ART.132 C.1 LETT. B) D.LGS.163/2006"},{"id":"195591","date":"2018-12-21T12:00:00Z","rationale":"ART.132 C.1 LETT. B) D.LGS.163/2006"}] |
| ocds-hu01ve-6935976 | None | [{"id":"204469","date":"2019-05-21T12:00:00Z"}] |
| ocds-hu01ve-6935987 | None | [{"id":"198372","date":"2018-07-27T12:00:00Z","rationale":"ART.132 C.1 LETT. B) D.LGS.163/2006"}] |
| ocds-hu01ve-6927439 | None | [{"id":"218939","date":"2018-08-07T12:00:00Z"}] |
| ocds-hu01ve-6927711 | None | [{"id":"204471","date":"2019-06-04T12:00:00Z"}] |
| ocds-hu01ve-6927897 | None | [{"id":"249441","date":"2020-02-05T12:00:00Z","rationale":"ART.132 C.1 LETT. A) D.LGS.163/2006"},{"id":"249442","date":"2021-03-10T12:00:00Z","rationale":"ART.132 C.1 LETT. B) D.LGS.163/2006"}] |
| ocds-hu01ve-6928091 | None | [{"id":"246286","date":"2020-08-24T12:00:00Z","rationale":"ALTRE CAUSE IMPREVISTE ED IMPREVEDIBILI"}] |
| ocds-hu01ve-6928292 | None | [{"id":"246091","date":"2019-09-06T12:00:00Z","rationale":"ALTRE CAUSE IMPREVISTE ED IMPREVEDIBILI"}] |
| ocds-hu01ve-6928778 | None | [{"id":"214524","date":"2019-12-13T12:00:00Z","rationale":"ALTRE CAUSE IMPREVISTE ED IMPREVEDIBILI"}] |
| ocds-hu01ve-6929163 | None | [{"id":"209699","date":"2019-01-21T12:00:00Z"}] |
| ocds-hu01ve-6929292 | None | [{"id":"209716","date":"2019-01-21T12:00:00Z"}] |
| ocds-hu01ve-6929361 | None | [{"id":"210178","date":"2019-01-21T12:00:00Z"}] |

## q8_roles
```sql
-- Which role combinations do parties carry? Are buyers/tenderers/suppliers cleanly separable?
WITH p AS (SELECT coalesce(from_json(party->'$.roles', '["VARCHAR"]'), []::VARCHAR[]) AS roles FROM r_party)
SELECT list_sort(roles) AS role_set, count(*) AS parties,
       round(100.0 * count(*) / (SELECT count(*) FROM p), 2) AS pct
FROM p GROUP BY 1 ORDER BY parties DESC LIMIT 25;
```
| role_set | parties | pct |
|---|---|---|
| ['payer'] | 561213 | 38.06 |
| ['buyer'] | 557762 | 37.82 |
| ['supplier'] | 355681 | 24.12 |
