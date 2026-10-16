-- Fourth pass (ticket A4 follow-up): why do 5,135 buyer references not resolve to a party?
-- Counts only. No identifier is selected, because the output is committed to a public repo.
-- Reads the staged database built by `make stage` and `make validate` (use --db, no setup block).

-- @query q24_buyer_ref_failures
-- Failures of the buyer reference, by id class, and what the process does carry.
WITH d AS (
  SELECT t.ocid, t.buyer_id,
         CASE WHEN regexp_matches(t.buyer_id, '^[0-9]{11}$') THEN '11 digits'
              WHEN length(t.buyer_id) = 16 THEN '16 characters' ELSE 'other' END AS id_class
  FROM tmp_release_check t
  WHERE t.ocid IS NOT NULL AND t.buyer_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM stg_party p WHERE p.ocid = t.ocid AND p.pid = t.buyer_id))
SELECT d.id_class, count(*) AS processes,
       count(DISTINCT d.buyer_id) AS distinct_buyer_ids,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM stg_party p
                  WHERE p.ocid = d.ocid AND p.role = 'buyer' AND p.id_raw = d.buyer_id))
         AS buyer_party_has_same_identifier,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM stg_party p
                  WHERE p.ocid = d.ocid AND p.role = 'buyer')) AS has_any_buyer_party,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM stg_party p WHERE p.ocid = d.ocid))
         AS no_parties_at_all
FROM d GROUP BY 1 ORDER BY 2 DESC;

-- @query q24b_failure_pid_shape
-- For failures where the process has a buyer party: how does its party id relate to buyer.id?
WITH d AS (
  SELECT t.ocid, t.buyer_id FROM tmp_release_check t
  WHERE t.ocid IS NOT NULL AND t.buyer_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM stg_party p WHERE p.ocid = t.ocid AND p.pid = t.buyer_id))
SELECT CASE WHEN p.pid = p.id_raw THEN 'party id equals its identifier'
            WHEN p.pid LIKE '%' || d.buyer_id || '%' THEN 'party id contains buyer.id'
            WHEN regexp_matches(p.pid, '^[0-9a-fA-F-]{36}$') THEN 'party id is a GUID'
            ELSE 'other' END AS shape,
       count(*) AS buyer_parties
FROM d JOIN stg_party p ON p.ocid = d.ocid AND p.role = 'buyer'
GROUP BY 1 ORDER BY 2 DESC;

-- @query q24c_normal_case
-- For processes that pass: what is the buyer party id compared with its identifier?
SELECT CASE WHEN p.pid = p.id_raw THEN 'party id equals its identifier' ELSE 'differs' END AS shape,
       count(*) AS processes
FROM tmp_release_check t JOIN stg_party p ON p.ocid = t.ocid AND p.pid = t.buyer_id
WHERE t.ocid IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;
