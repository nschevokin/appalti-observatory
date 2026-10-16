-- Ticket A5: coverage. Records per period and populatedness per field, from the records that
-- passed Gate 1 (the clean_* views). Append-only: every run adds rows under a new run_id.
-- Counts only; nothing here can identify a party. Placeholders are filled in by coverage.py.

-- @step coverage_table
CREATE TABLE IF NOT EXISTS coverage (
  run_id VARCHAR, measured_at VARCHAR, sha256 VARCHAR,
  clock VARCHAR, period VARCHAR, unit VARCHAR, field VARCHAR,
  n_total BIGINT, n_populated BIGINT);

-- @step coverage_processes
-- Process-level fields, on two clocks: the year the tender started and the release year.
INSERT INTO coverage
WITH buyer_postal AS (
  SELECT DISTINCT ocid FROM clean_party WHERE role = 'buyer' AND postal_code IS NOT NULL),
proc AS (
  SELECT r.ocid,
         coalesce(CAST(r.tender_start_year AS VARCHAR), 'undated') AS p_tender,
         coalesce(CAST(r.release_year AS VARCHAR), 'undated') AS p_release,
         true AS records,
         r.tender_amount IS NOT NULL AS tender_amount,
         r.tender_start_raw IS NOT NULL AS tender_start_date,
         r.procedure_code IS NOT NULL AS procedure_code,
         r.cpv_division IS NOT NULL AS cpv_division,
         r.number_of_tenderers IS NOT NULL AS number_of_tenderers,
         b.ocid IS NOT NULL AS buyer_postal_code
  FROM clean_release r LEFT JOIN buyer_postal b ON b.ocid = r.ocid),
long AS (
  SELECT 'tender_start_year' AS clock, p_tender AS period, u.field, u.ok
  FROM (UNPIVOT proc ON records, tender_amount, tender_start_date, procedure_code, cpv_division,
                        number_of_tenderers, buyer_postal_code INTO NAME field VALUE ok) u
  UNION ALL
  SELECT 'release_year', p_release, u.field, u.ok
  FROM (UNPIVOT proc ON records, tender_amount, tender_start_date, procedure_code, cpv_division,
                        number_of_tenderers, buyer_postal_code INTO NAME field VALUE ok) u)
SELECT '$RUN_ID', '$MEASURED_AT', '$SHA', clock, period, 'process', field,
       count(*), count(*) FILTER (WHERE ok)
FROM long GROUP BY clock, period, field;

-- @step coverage_awards
-- Award-level fields on the analysis clock, the award year (D015).
INSERT INTO coverage
WITH linked AS (SELECT DISTINCT ocid, award_id FROM clean_contract),
aw AS (
  SELECT coalesce(CAST(a.award_year AS VARCHAR), 'undated') AS period,
         true AS records,
         a.amount IS NOT NULL AS award_amount,
         (a.award_date_raw IS NOT NULL AND a.award_year IS NOT NULL) AS award_date,
         a.n_suppliers > 0 AS has_supplier,
         l.ocid IS NOT NULL AS has_contract
  FROM clean_award a LEFT JOIN linked l ON l.ocid = a.ocid AND l.award_id = a.award_id)
SELECT '$RUN_ID', '$MEASURED_AT', '$SHA', 'award_year', period, 'award', u.field,
       count(*), count(*) FILTER (WHERE u.ok)
FROM (UNPIVOT aw ON records, award_amount, award_date, has_supplier, has_contract
      INTO NAME field VALUE ok) u
GROUP BY period, u.field;
