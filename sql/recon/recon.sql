-- Day-1 reconnaissance. Read-only measurements; nothing here is pipeline code.
-- Blocks start with "-- @setup <name>" (run silently) or "-- @query <name>" (result recorded).
-- ASSUMPTION to verify with q0: each line is one OCDS release/record with ocid, tender,
-- awards, contracts, parties at the top level. If q0 shows a wrapper key (e.g. "releases"
-- or "records"), fix the views in the setup blocks and rerun.
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

CREATE OR REPLACE VIEW r_contract AS
SELECT ocid, unnest(from_json(contracts, '["JSON"]')) AS contract
FROM (SELECT doc->>'$.ocid' AS ocid, doc->'$.contracts' AS contracts FROM raw);

-- @query q0_structure
-- Top-level keys and how often each is present.
SELECT k AS top_level_key, count(*) AS n,
       round(100.0 * count(*) / (SELECT count(*) FROM raw), 2) AS pct_of_lines
FROM (SELECT unnest(json_keys(doc)) AS k FROM raw)
GROUP BY k ORDER BY n DESC;

-- @query q1_ocid_unique
SELECT count(*) AS lines,
       count(doc->>'$.ocid') AS with_ocid,
       count(DISTINCT doc->>'$.ocid') AS distinct_ocid,
       count(*) - count(DISTINCT doc->>'$.ocid') AS surplus_lines
FROM raw;

-- @query q1_ocid_duplicates_top
SELECT doc->>'$.ocid' AS ocid, count(*) AS lines
FROM raw GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC LIMIT 10;

-- @query q2_identifier_by_role
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

-- @query q2_identifier_schemes
SELECT coalesce(party->>'$.identifier.scheme', '<null>') AS scheme,
       count(*) AS n,
       count(nullif(trim(party->>'$.identifier.id'), '')) AS with_id
FROM r_party GROUP BY 1 ORDER BY n DESC LIMIT 30;

-- @query q2_identifier_samples
-- Eyeball the id format per scheme (is it a fiscal code, a VAT number, junk?).
SELECT scheme, id FROM (
  SELECT party->>'$.identifier.scheme' AS scheme,
         party->>'$.identifier.id' AS id,
         row_number() OVER (PARTITION BY party->>'$.identifier.scheme' ORDER BY random()) AS rn
  FROM r_party WHERE nullif(trim(party->>'$.identifier.id'), '') IS NOT NULL)
WHERE rn <= 5 ORDER BY scheme;

-- @query q3_year_counts
-- Real counts per calendar year on three different clocks.
SELECT 'process_by_tender_period_start' AS basis, yr(doc->>'$.tender.tenderPeriod.startDate') AS year, count(*) AS n
FROM raw GROUP BY 2
UNION ALL
SELECT 'process_by_release_date', yr(doc->>'$.date'), count(*) FROM raw GROUP BY 2
UNION ALL
SELECT 'award_by_award_date', yr(award->>'$.date'), count(*) FROM r_award GROUP BY 2
ORDER BY basis, year;

-- @query q4_tenderers_by_year
-- Per-year populatedness of tender.numberOfTenderers (year = tender start, else release date).
SELECT coalesce(yr(doc->>'$.tender.tenderPeriod.startDate'), yr(doc->>'$.date')) AS year,
       count(*) AS tenders,
       count(doc->>'$.tender.numberOfTenderers') AS with_n_tenderers,
       round(100.0 * count(doc->>'$.tender.numberOfTenderers') / count(*), 2) AS pct_populated
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- @query q4_tenderers_values
SELECT doc->>'$.tender.numberOfTenderers' AS n_tenderers, count(*) AS n
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY n DESC LIMIT 15;

-- @query q5_amounts_award
SELECT coalesce(award->>'$.value.currency', '<null>') AS currency,
       count(*) AS awards,
       count(*) FILTER (WHERE (award->>'$.value.amount') IS NULL) AS null_amount,
       count(award->>'$.value.amount') - count(try_cast(award->>'$.value.amount' AS DOUBLE)) AS non_numeric,
       count(*) FILTER (WHERE try_cast(award->>'$.value.amount' AS DOUBLE) < 0) AS negative,
       count(*) FILTER (WHERE try_cast(award->>'$.value.amount' AS DOUBLE) = 0) AS zero,
       round(median(try_cast(award->>'$.value.amount' AS DOUBLE)), 0) AS median_amount,
       round(max(try_cast(award->>'$.value.amount' AS DOUBLE)), 0) AS max_amount
FROM r_award GROUP BY 1 ORDER BY awards DESC;

-- @query q5_amounts_largest
-- Outliers: the ten largest award amounts (typos, cents-as-euro, framework ceilings).
SELECT ocid, award->>'$.id' AS award_id, award->>'$.value.currency' AS currency,
       try_cast(award->>'$.value.amount' AS DOUBLE) AS amount
FROM r_award ORDER BY amount DESC NULLS LAST LIMIT 10;

-- @query q6_award_contract_link
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

-- @query q6_contract_share_by_award_year
-- Is the contract stage published selectively over time?
WITH a AS (SELECT ocid, award->>'$.id' AS award_id, yr(award->>'$.date') AS year FROM r_award),
     c AS (SELECT ocid, contract->>'$.awardID' AS award_id FROM r_contract)
SELECT year, count(*) AS awards,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM c WHERE c.ocid = a.ocid AND c.award_id = a.award_id)) AS with_contract,
       round(100.0 * count(*) FILTER (WHERE EXISTS (SELECT 1 FROM c WHERE c.ocid = a.ocid AND c.award_id = a.award_id)) / count(*), 2) AS pct_with_contract
FROM a GROUP BY year ORDER BY year;

-- @query q7_amendments_where
-- Where do amendments live? (tender / awards / contracts level)
SELECT 'tender' AS level, coalesce(sum(json_array_length(doc->'$.tender.amendments')), 0) AS amendments FROM raw
UNION ALL SELECT 'award', coalesce(sum(json_array_length(award->'$.amendments')), 0) FROM r_award
UNION ALL SELECT 'contract', coalesce(sum(json_array_length(contract->'$.amendments')), 0) FROM r_contract;

-- @query q7_amendment_keys
SELECT k AS amendment_key, count(*) AS n
FROM (SELECT unnest(json_keys(am)) AS k
      FROM (SELECT unnest(from_json(contract->'$.amendments', '["JSON"]')) AS am FROM r_contract))
GROUP BY k ORDER BY n DESC;

-- @query q7_amendment_samples
-- READ THESE BY EYE: does an amendment carry a restated value or only a delta/change list?
SELECT ocid, contract->>'$.value.amount' AS contract_value, contract->'$.amendments' AS amendments
FROM r_contract WHERE json_array_length(contract->'$.amendments') > 0
LIMIT 15;

-- @query q8_roles
-- Which role combinations do parties carry? Are buyers/tenderers/suppliers cleanly separable?
WITH p AS (SELECT coalesce(from_json(party->'$.roles', '["VARCHAR"]'), []::VARCHAR[]) AS roles FROM r_party)
SELECT list_sort(roles) AS role_set, count(*) AS parties,
       round(100.0 * count(*) / (SELECT count(*) FROM p), 2) AS pct
FROM p GROUP BY 1 ORDER BY parties DESC LIMIT 25;
