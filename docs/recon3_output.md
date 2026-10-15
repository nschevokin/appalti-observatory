# Recon output
Run date: 2026-10-15T17:48:28
Input: `data/raw/full.jsonl.gz`
DuckDB: 1.5.6

## q18_award_sum_vs_tender
```sql
-- Per process: sum of award amounts against the tender's own amount. An award far above its
-- tender's value is the signature of a unit or decimal error (informs D017).
WITH p AS (
  SELECT try_cast(doc->>'$.tender.value.amount' AS DOUBLE) AS t_amt,
         list_sum(list_transform(from_json(doc->'$.awards', '["JSON"]'),
                  a -> try_cast(json_extract_string(a, '$.value.amount') AS DOUBLE))) AS a_sum
  FROM raw WHERE (doc->'$.awards') IS NOT NULL)
SELECT CASE WHEN t_amt IS NULL OR t_amt <= 0 THEN '0 no usable tender amount'
            WHEN a_sum IS NULL THEN '1 no award amount'
            WHEN a_sum <= t_amt THEN '2 awards at or below tender'
            WHEN a_sum <= 1.5 * t_amt THEN '3 up to 1.5x tender'
            WHEN a_sum <= 2 * t_amt THEN '4 1.5x to 2x'
            WHEN a_sum <= 10 * t_amt THEN '5 2x to 10x'
            WHEN a_sum <= 100 * t_amt THEN '6 10x to 100x'
            ELSE '7 over 100x tender' END AS award_vs_tender,
       count(*) AS processes,
       round(sum(a_sum)) AS awards_total_eur
FROM p GROUP BY 1 ORDER BY 1;
```
| award_vs_tender | processes | awards_total_eur |
|---|---|---|
| 0 no usable tender amount | 25 | 241851210.0 |
| 1 no award amount | 139 | None |
| 2 awards at or below tender | 267722 | 253583277936.0 |
| 3 up to 1.5x tender | 5721 | 11483034600.0 |
| 4 1.5x to 2x | 327 | 1561719826.0 |
| 5 2x to 10x | 212 | 3407225567.0 |
| 6 10x to 100x | 61 | 11175942687.0 |
| 7 over 100x tender | 33 | 76666529421.0 |

## q19_short_ids_padding
```sql
-- Digit-only ids shorter than 11: do they match an 11-digit id once zero-padded
-- (leading zeros lost somewhere upstream)?
WITH s AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{1,10}$')),
     f AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{11}$'))
SELECT (SELECT count(*) FROM s) AS short_ids,
       (SELECT count(*) FROM s JOIN f ON lpad(s.id, 11, '0') = f.id) AS short_ids_matching_padded;
```
| short_ids | short_ids_matching_padded |
|---|---|
| 530 | 22 |

## q20_buyer_address_keys
```sql
-- Where could a buyer's region live? (public bodies only; q17 probed a field that may not exist)
SELECT k AS address_key, count(*) AS n
FROM (SELECT unnest(json_keys(party->'$.address')) AS k FROM r_party
      WHERE (party->>'$.roles') LIKE '%buyer%' AND json_type(party->'$.address') = 'OBJECT')
GROUP BY k ORDER BY n DESC;
```
| address_key | n |
|---|---|
| postalCode | 557762 |
| locality | 557762 |
| countryName | 557762 |
| streetAddress | 557759 |

## q20_buyer_address_samples
```sql
SELECT party->'$.address' AS address
FROM r_party
WHERE (party->>'$.roles') LIKE '%buyer%' AND regexp_matches(party->>'$.identifier.id', '^[0-9]{11}$')
  AND json_type(party->'$.address') = 'OBJECT'
ORDER BY random() LIMIT 5;
```
| address |
|---|
| {"locality":"BORGO PACE","postalCode":"61040","countryName":"ITALY","streetAddress":"PIAZZA DEL PINO N. 3"} |
| {"locality":"VILLANOVA MONFERRATO","postalCode":"15030","countryName":"ITALY","streetAddress":"PIAZZA FINAZZI 8"} |
| {"locality":"TOLENTINO","postalCode":"62029","countryName":"ITALY","streetAddress":"LOCALITA' PIANE DI CHIENTI"} |
| {"locality":"TRAPANI","postalCode":"91100","countryName":"ITALY","streetAddress":"VIA MAZZINI N 1"} |
| {"locality":"BORGO VALBELLUNA","postalCode":"32026","countryName":"ITALY","streetAddress":"QUARTIERE EUROPA 5"} |

## q21_buyer_additional_identifiers
```sql
-- Buyers carry additionalIdentifiers (557,815 on parties): which schemes?
SELECT coalesce(ai->>'$.scheme', '<null>') AS scheme, count(*) AS n
FROM (SELECT unnest(from_json(party->'$.additionalIdentifiers', '["JSON"]')) AS ai FROM r_party
      WHERE (party->>'$.roles') LIKE '%buyer%')
GROUP BY 1 ORDER BY n DESC LIMIT 10;
```
| scheme | n |
|---|---|
| AUSA | 557762 |

## q22_value_by_supplier_count
```sql
-- How much awarded value sits on awards with several suppliers (sizes the D006 choice)?
WITH a AS (SELECT coalesce(json_array_length(award->'$.suppliers'), 0) AS n,
                  try_cast(award->>'$.value.amount' AS DOUBLE) AS amt FROM r_award)
SELECT CASE WHEN n = 0 THEN '0 suppliers' WHEN n = 1 THEN '1 supplier'
            WHEN n <= 5 THEN '2-5 suppliers' ELSE '6+ suppliers' END AS suppliers_on_award,
       count(*) AS awards,
       round(sum(amt)) AS total_eur,
       round(100.0 * sum(amt) / (SELECT sum(amt) FROM a), 2) AS pct_of_value
FROM a GROUP BY 1 ORDER BY 1;
```
| suppliers_on_award | awards | total_eur | pct_of_value |
|---|---|---|---|
| 0 suppliers | 870 | 671414324.0 | 0.19 |
| 1 supplier | 293006 | 259936209640.0 | 72.58 |
| 2-5 suppliers | 27566 | 69346713536.0 | 19.36 |
| 6+ suppliers | 2588 | 28165243746.0 | 7.86 |

## q23_procedure_mix_by_year
```sql
-- procurementMethod is empty; the procedure lives in procurementMethodDetails as 'COD:n ; TITLE:..'.
-- Share of the top codes by tender start year: a preview of composition drift (Gate 2).
WITH t AS (
  SELECT yr(doc->>'$.tender.tenderPeriod.startDate') AS year,
         try_cast(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1) AS INTEGER) AS cod
  FROM raw WHERE (doc->'$.tender') IS NOT NULL)
SELECT year, count(*) AS tenders,
       round(100.0 * count(*) FILTER (WHERE cod = 24) / count(*), 1) AS pct_direct_24,
       round(100.0 * count(*) FILTER (WHERE cod = 27) / count(*), 1) AS pct_call_off_27,
       round(100.0 * count(*) FILTER (WHERE cod = 34) / count(*), 1) AS pct_negotiated_below_34,
       round(100.0 * count(*) FILTER (WHERE cod = 4) / count(*), 1) AS pct_negotiated_no_notice_4,
       round(100.0 * count(*) FILTER (WHERE cod = 1) / count(*), 1) AS pct_open_1,
       round(100.0 * count(*) FILTER (WHERE cod IS NULL OR cod NOT IN (24, 27, 34, 4, 1)) / count(*), 1) AS pct_other
FROM t GROUP BY year ORDER BY year;
```
| year | tenders | pct_direct_24 | pct_call_off_27 | pct_negotiated_below_34 | pct_negotiated_no_notice_4 | pct_open_1 | pct_other |
|---|---|---|---|---|---|---|---|
| 2018 | 109404 | 16.2 | 33.3 | 0.0 | 17.6 | 8.5 | 24.3 |
| 2019 | 108394 | 21.7 | 28.4 | 13.3 | 13.8 | 9.8 | 12.9 |
| 2020 | 89362 | 20.8 | 37.0 | 17.8 | 10.6 | 8.1 | 5.9 |
| 2021 | 84619 | 42.3 | 23.1 | 16.6 | 6.0 | 7.1 | 4.9 |
| 2022 | 139431 | 40.1 | 29.3 | 14.2 | 5.6 | 6.7 | 4.1 |
| 2023 | 31625 | 60.0 | 20.8 | 9.6 | 3.6 | 3.4 | 2.5 |
| 2024 | 27 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## q23_distinct_procedure_codes
```sql
SELECT count(DISTINCT regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1)) AS distinct_codes,
       count(*) FILTER (WHERE (doc->>'$.tender.procurementMethodDetails') IS NULL) AS tenders_without_details
FROM raw WHERE (doc->'$.tender') IS NOT NULL;
```
| distinct_codes | tenders_without_details |
|---|---|
| 30 | 0 |
