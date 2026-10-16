-- Ticket B3 (continued): the award fact table and the supplier bridge (D021, D025, D026).
-- Rebuilt from the clean_* views and the entity table on every run.

-- @step cap_region
CREATE OR REPLACE TABLE cap_region AS
SELECT * FROM read_csv('$CAP_CSV', header = true,
                       columns = {'prefix': 'VARCHAR', 'region': 'VARCHAR'});

-- @step buyer_of_process
CREATE OR REPLACE TABLE tmp_buyer AS
SELECT t.ocid, e.entity_id AS buyer_entity_id,
       CASE WHEN regexp_matches(k.postal_code, '^[0-9]{5}$') THEN left(k.postal_code, 2) END
         AS postal_prefix
FROM tmp_release_check t
JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
LEFT JOIN entity e ON e.entity_key = k.entity_key
WHERE t.ocid IS NOT NULL;

-- @step fact_award
CREATE OR REPLACE TABLE fact_award AS
WITH sums AS (SELECT ocid, sum(amount) AS award_sum FROM clean_award GROUP BY ocid)
SELECT a.ocid, a.award_id, a.award_year,
       b.buyer_entity_id,
       CASE WHEN a.currency = 'EUR' THEN a.amount END AS amount_eur,
       r.tender_amount,
       r.cpv_division,
       r.procedure_code,
       coalesce(c.region, 'unknown') AS region,
       r.number_of_tenderers AS n_tenderers,
       CASE WHEN r.number_of_tenderers IS NULL THEN NULL
            ELSE r.number_of_tenderers = 1 END AS single_bidder,
       a.n_suppliers,
       coalesce(r.tender_amount > 0 AND s.award_sum > 10 * r.tender_amount, false)
         AS inconsistent_amount,
       (nullif(trim(a.award_date_raw), '') IS NULL
        OR NOT coalesce(try_cast(left(a.award_date_raw, 10) AS DATE)
                        BETWEEN DATE '$MIN_DATE' AND DATE '$PUB_DATE', false)) AS award_date_flagged,
       '$RUN_ID' AS run_id
FROM clean_award a
JOIN clean_release r ON r.ocid = a.ocid
LEFT JOIN sums s ON s.ocid = a.ocid
LEFT JOIN tmp_buyer b ON b.ocid = a.ocid
LEFT JOIN cap_region c ON c.prefix = b.postal_prefix;

-- @step fact_award_supplier
-- One row per supplier per award; the amount is split equally among the distinct suppliers.
CREATE OR REPLACE TABLE fact_award_supplier AS
WITH linked AS (
  SELECT DISTINCT cs.ocid, cs.award_id, e.entity_id AS supplier_entity_id
  FROM clean_award_supplier cs
  JOIN party_key k ON k.ocid = cs.ocid AND k.pid = cs.supplier_pid
  JOIN entity e ON e.entity_key = k.entity_key)
SELECT ocid, award_id, supplier_entity_id,
       1.0 / count(*) OVER (PARTITION BY ocid, award_id) AS share,
       '$RUN_ID' AS run_id
FROM linked;
