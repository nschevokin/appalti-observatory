-- Fifth pass (before week 3): the procedure codes with their titles (D023), and why
-- 24,231 awards have region 'unknown'. Counts and code titles only; no names, no identifiers.
-- Reads the database built by `make entities` (tables raw, fact_award, party_key, cap_region).

-- @query q30_procedure_codes
-- Every COD value with its title and how many tenders carry it.
WITH t AS (
  SELECT try_cast(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1)
                  AS INTEGER) AS cod,
         trim(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'TITLE:(.*)$', 1)) AS title
  FROM raw WHERE (doc->'$.tender') IS NOT NULL)
SELECT cod, title, count(*) AS tenders,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
FROM t GROUP BY 1, 2 ORDER BY 3 DESC;

-- @query q31_procedure_codes_in_awards
-- Same, on awards that made it into fact_award (the population the indicators use).
SELECT procedure_code AS cod, count(*) AS awards,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct,
       round(sum(amount_eur) / 1e9, 2) AS value_bn_eur
FROM fact_award GROUP BY 1 ORDER BY 2 DESC;

-- @query q32_unknown_region_cause
-- Why is the region unknown? One row per cause, awards counted.
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT CASE WHEN b.ocid IS NULL THEN 'no buyer party found'
            WHEN b.postal IS NULL OR trim(b.postal) = '' THEN 'postal code missing'
            WHEN NOT regexp_matches(b.postal, '^[0-9]{5}$') THEN 'postal code not 5 digits'
            ELSE 'prefix not in cap_region' END AS cause,
       count(*) AS awards
FROM fact_award f LEFT JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' GROUP BY 1 ORDER BY 2 DESC;

-- @query q33_unmapped_prefixes
-- For the last cause: the most frequent two-digit prefixes missing from the table.
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT left(b.postal, 2) AS prefix, count(*) AS awards
FROM fact_award f JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' AND regexp_matches(b.postal, '^[0-9]{5}$')
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;

-- @query q34_unknown_region_by_year
SELECT award_year, count(*) AS awards,
       count(*) FILTER (WHERE region = 'unknown') AS unknown_region,
       round(100.0 * count(*) FILTER (WHERE region = 'unknown') / count(*), 1) AS pct_unknown
FROM fact_award GROUP BY 1 ORDER BY 1;
