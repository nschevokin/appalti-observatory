-- Ticket C1: the four indicators, each on both clocks (D032), each carrying its n and its
-- populatedness. Rebuilt from fact_award and fact_award_supplier on every run.
-- Substitutions: $PROC_CSV, $RUN_ID, $FIRST, $LAST, $LEGAL_RE.
-- Money: the headline excludes processes flagged inconsistent_amount (D025); `all` includes them.

-- @step proc_class
CREATE OR REPLACE TABLE proc_class AS
SELECT * FROM read_csv('$PROC_CSV', header = true,
                       columns = {'code': 'INTEGER', 'class': 'VARCHAR'});

-- @step ind_unit
-- One row per award per clock; awards outside the window or without a year are left out here
-- and counted separately by indicators.py.
CREATE OR REPLACE TABLE ind_unit AS
WITH b AS (
  SELECT f.*, CASE WHEN f.procedure_code IS NULL THEN NULL
                   ELSE coalesce(pc.class, 'other') END AS proc_class
  FROM fact_award f LEFT JOIN proc_class pc ON pc.code = f.procedure_code)
SELECT 'award_year' AS clock, award_year AS period, ocid, award_id, region, cpv_division,
       proc_class, amount_eur, inconsistent_amount, n_tenderers, single_bidder, n_suppliers
FROM b WHERE award_year BETWEEN $FIRST AND $LAST
UNION ALL
SELECT 'tender_year', tender_year, ocid, award_id, region, cpv_division,
       proc_class, amount_eur, inconsistent_amount, n_tenderers, single_bidder, n_suppliers
FROM b WHERE tender_year BETWEEN $FIRST AND $LAST;

-- @step ind_populatedness
-- Per indicator, clock and period: records and how many carry the field the indicator needs.
CREATE OR REPLACE TABLE ind_populatedness AS
SELECT 'awarded_value' AS indicator, clock, period, count(*) AS n,
       count(amount_eur) AS n_populated FROM ind_unit GROUP BY 2, 3
UNION ALL
SELECT 'single_bidder', clock, period, count(*), count(single_bidder) FROM ind_unit GROUP BY 2, 3
UNION ALL
SELECT 'concentration', clock, period, count(*),
       count(*) FILTER (WHERE amount_eur IS NOT NULL AND n_suppliers > 0) FROM ind_unit GROUP BY 2, 3
UNION ALL
SELECT 'procedure_mix', clock, period, count(*), count(proc_class) FROM ind_unit GROUP BY 2, 3;

-- @step ind_composition
-- The sector mix per period (award counts by CPV division); Gate 2 measures drift on it.
CREATE OR REPLACE TABLE ind_composition AS
SELECT clock, period, coalesce(cpv_division, '??') AS cpv_division, count(*) AS n
FROM ind_unit GROUP BY 1, 2, 3;

-- @step ind_name_group
-- Upper bound for concentration: supplier ids that share a legal-form name are counted as one.
CREATE OR REPLACE TABLE ind_name_group AS
WITH e AS (
  SELECT entity_id, canonical_name FROM entity
  WHERE regexp_matches(identifier_id, '^[0-9]{11}$') AND canonical_name IS NOT NULL
    AND regexp_matches(upper(regexp_replace(canonical_name, '[.'']', '', 'g')), '$LEGAL_RE'))
SELECT entity_id, 'N:' || canonical_name AS grp FROM e
WHERE canonical_name IN (SELECT canonical_name FROM e GROUP BY 1 HAVING count(*) > 1);

-- @step indicator_value
CREATE OR REPLACE TABLE indicator_value (
  indicator VARCHAR, clock VARCHAR, period INTEGER, slice_type VARCHAR, slice_value VARCHAR,
  variant VARCHAR, value DOUBLE, n BIGINT, run_id VARCHAR);

-- awarded value: three variants, overall and by region
INSERT INTO indicator_value
SELECT 'awarded_value', clock, period, 'all', 'all', v.variant,
       CASE v.variant WHEN 'headline' THEN sum(amount_eur) FILTER (WHERE NOT inconsistent_amount)
                      WHEN 'all' THEN sum(amount_eur)
                      ELSE sum(amount_eur) FILTER (WHERE inconsistent_amount) END,
       CASE v.variant WHEN 'headline' THEN count(*) FILTER (WHERE NOT inconsistent_amount)
                      WHEN 'all' THEN count(*)
                      ELSE count(*) FILTER (WHERE inconsistent_amount) END,
       '$RUN_ID'
FROM ind_unit CROSS JOIN (VALUES ('headline'), ('all'), ('flagged')) v(variant)
GROUP BY clock, period, v.variant;

INSERT INTO indicator_value
SELECT 'awarded_value', clock, period, 'region', region, 'headline',
       sum(amount_eur) FILTER (WHERE NOT inconsistent_amount),
       count(*) FILTER (WHERE NOT inconsistent_amount), '$RUN_ID'
FROM ind_unit GROUP BY clock, period, region;

-- single bidder: the denominator is awards with a published tenderer count
INSERT INTO indicator_value
SELECT 'single_bidder', clock, period, 'all', 'all', 'share',
       sum(single_bidder::INTEGER)::DOUBLE / nullif(count(single_bidder), 0),
       count(single_bidder), '$RUN_ID'
FROM ind_unit GROUP BY clock, period;

-- concentration: top five suppliers' share of the slice's headline value (D021, equal split)
INSERT INTO indicator_value
WITH tot AS (
  SELECT clock, period, sum(amount_eur) FILTER (WHERE NOT inconsistent_amount) AS total
  FROM ind_unit GROUP BY 1, 2),
base AS (
  SELECT u.clock, u.period, s.supplier_entity_id AS sid, g.grp, u.amount_eur * s.share AS v,
         u.ocid, u.award_id
  FROM ind_unit u
  JOIN fact_award_supplier s ON s.ocid = u.ocid AND s.award_id = u.award_id
  LEFT JOIN ind_name_group g ON g.entity_id = s.supplier_entity_id
  WHERE NOT u.inconsistent_amount AND u.amount_eur > 0),
used AS (SELECT clock, period, count(DISTINCT (ocid, award_id)) AS n FROM base GROUP BY 1, 2),
pt AS (SELECT clock, period, sid AS k, sum(v) AS v FROM base GROUP BY 1, 2, 3),
mg AS (SELECT clock, period, coalesce(grp, sid) AS k, sum(v) AS v FROM base GROUP BY 1, 2, 3),
ranked AS (
  SELECT 'point' AS variant, clock, period, v,
         row_number() OVER (PARTITION BY clock, period ORDER BY v DESC, k) AS rk FROM pt
  UNION ALL
  SELECT 'merged_upper', clock, period, v,
         row_number() OVER (PARTITION BY clock, period ORDER BY v DESC, k) FROM mg)
SELECT 'concentration', r.clock, r.period, 'all', 'all', r.variant,
       sum(r.v) / t.total, u.n, '$RUN_ID'
FROM ranked r JOIN tot t USING (clock, period) JOIN used u USING (clock, period)
WHERE r.rk <= 5 GROUP BY r.clock, r.period, r.variant, t.total, u.n;

-- procedure mix: share of headline value per class among awards that carry a class
INSERT INTO indicator_value
WITH c AS (
  SELECT clock, period, proc_class, sum(amount_eur) AS v, count(*) AS n
  FROM ind_unit WHERE NOT inconsistent_amount AND proc_class IS NOT NULL
  GROUP BY 1, 2, 3)
SELECT 'procedure_mix', clock, period, 'all', 'all', proc_class,
       v / nullif(sum(v) OVER (PARTITION BY clock, period), 0), n, '$RUN_ID'
FROM c;
