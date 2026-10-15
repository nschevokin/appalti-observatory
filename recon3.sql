-- Third-pass reconnaissance (ticket A1c). Written after the first two passes, so it is NOT part
-- of the pre-registered rules. Every query scans once; none joins awards to raw documents
-- (that join ran out of memory in pass two). Counts and public bodies only: no natural persons.
-- $RAW_FILE is substituted by scripts/run_recon.py.

-- @setup raw
CREATE OR REPLACE TABLE raw AS
SELECT line::JSON AS doc
FROM read_csv('$RAW_FILE', columns={'line': 'VARCHAR'}, delim=E'\x07',
              quote='', escape='', header=false, max_line_size=104857600);

-- @setup macros
CREATE OR REPLACE MACRO yr(x) AS try_cast(left(x, 4) AS INTEGER);

-- @setup views
CREATE OR REPLACE VIEW r_party AS
SELECT ocid, unnest(from_json(parties, '["JSON"]')) AS party
FROM (SELECT doc->>'$.ocid' AS ocid, doc->'$.parties' AS parties FROM raw);

CREATE OR REPLACE VIEW r_award AS
SELECT ocid, unnest(from_json(awards, '["JSON"]')) AS award
FROM (SELECT doc->>'$.ocid' AS ocid, doc->'$.awards' AS awards FROM raw);

CREATE OR REPLACE VIEW r_party2 AS
SELECT ocid,
       party->>'$.id' AS pid,
       from_json(party->'$.roles', '["VARCHAR"]')[1] AS role,
       party->>'$.identifier.scheme' AS scheme,
       nullif(trim(party->>'$.identifier.id'), '') AS id,
       upper(trim(coalesce(party->>'$.name', party->>'$.identifier.legalName'))) AS name
FROM r_party;

-- @query q18_award_sum_vs_tender
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

-- @query q19_short_ids_padding
-- Digit-only ids shorter than 11: do they match an 11-digit id once zero-padded
-- (leading zeros lost somewhere upstream)?
WITH s AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{1,10}$')),
     f AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{11}$'))
SELECT (SELECT count(*) FROM s) AS short_ids,
       (SELECT count(*) FROM s JOIN f ON lpad(s.id, 11, '0') = f.id) AS short_ids_matching_padded;

-- @query q20_buyer_address_keys
-- Where could a buyer's region live? (public bodies only; q17 probed a field that may not exist)
SELECT k AS address_key, count(*) AS n
FROM (SELECT unnest(json_keys(party->'$.address')) AS k FROM r_party
      WHERE (party->>'$.roles') LIKE '%buyer%' AND json_type(party->'$.address') = 'OBJECT')
GROUP BY k ORDER BY n DESC;

-- @query q20_buyer_address_samples
SELECT party->'$.address' AS address
FROM r_party
WHERE (party->>'$.roles') LIKE '%buyer%' AND regexp_matches(party->>'$.identifier.id', '^[0-9]{11}$')
  AND json_type(party->'$.address') = 'OBJECT'
ORDER BY random() LIMIT 5;

-- @query q21_buyer_additional_identifiers
-- Buyers carry additionalIdentifiers (557,815 on parties): which schemes?
SELECT coalesce(ai->>'$.scheme', '<null>') AS scheme, count(*) AS n
FROM (SELECT unnest(from_json(party->'$.additionalIdentifiers', '["JSON"]')) AS ai FROM r_party
      WHERE (party->>'$.roles') LIKE '%buyer%')
GROUP BY 1 ORDER BY n DESC LIMIT 10;

-- @query q22_value_by_supplier_count
-- How much awarded value sits on awards with several suppliers (sizes the D006 choice)?
WITH a AS (SELECT coalesce(json_array_length(award->'$.suppliers'), 0) AS n,
                  try_cast(award->>'$.value.amount' AS DOUBLE) AS amt FROM r_award)
SELECT CASE WHEN n = 0 THEN '0 suppliers' WHEN n = 1 THEN '1 supplier'
            WHEN n <= 5 THEN '2-5 suppliers' ELSE '6+ suppliers' END AS suppliers_on_award,
       count(*) AS awards,
       round(sum(amt)) AS total_eur,
       round(100.0 * sum(amt) / (SELECT sum(amt) FROM a), 2) AS pct_of_value
FROM a GROUP BY 1 ORDER BY 1;

-- @query q23_procedure_mix_by_year
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

-- @query q23_distinct_procedure_codes
SELECT count(DISTINCT regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1)) AS distinct_codes,
       count(*) FILTER (WHERE (doc->>'$.tender.procurementMethodDetails') IS NULL) AS tenders_without_details
FROM raw WHERE (doc->'$.tender') IS NOT NULL;
