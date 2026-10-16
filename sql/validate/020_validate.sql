-- Ticket A4: Gate 1. Every rule writes its failures to rejected_record with a reason code;
-- nothing is dropped silently. A rejected process is excluded from the clean_* views.
-- Placeholders ($MIN_DATE, $PUB_DATE, $CURRENCIES) are filled in by src/appalti/validate.py.

-- @step release_check
-- One scan of raw for the fields staging does not keep.
CREATE OR REPLACE TABLE tmp_release_check AS
SELECT nullif(trim(doc->>'$.ocid'), '') AS ocid,
       doc->>'$.date' AS date_raw,
       doc->>'$.buyer.id' AS buyer_id,
       concat_ws(', ',
         CASE WHEN nullif(trim(doc->>'$.ocid'), '') IS NULL THEN 'ocid' END,
         CASE WHEN nullif(trim(doc->>'$.id'), '') IS NULL THEN 'id' END,
         CASE WHEN nullif(trim(doc->>'$.date'), '') IS NULL THEN 'date' END,
         CASE WHEN coalesce(json_array_length(doc->'$.tag'), 0) = 0 THEN 'tag' END,
         CASE WHEN nullif(trim(doc->>'$.initiationType'), '') IS NULL THEN 'initiationType' END
       ) AS missing
FROM raw;

-- @step rejected_record
CREATE OR REPLACE TABLE rejected_record (
  ocid VARCHAR, level VARCHAR, object_id VARCHAR, reason VARCHAR, detail VARCHAR);

-- @step rule_missing_required
INSERT INTO rejected_record
SELECT ocid, 'release', NULL, 'missing_required', 'missing: ' || missing
FROM tmp_release_check WHERE missing <> '';

-- @step rule_date_out_of_range
INSERT INTO rejected_record
SELECT ocid, 'release', NULL, 'date_out_of_range', date_raw
FROM tmp_release_check
WHERE nullif(trim(date_raw), '') IS NOT NULL
  AND NOT coalesce(try_cast(left(date_raw, 10) AS DATE) BETWEEN DATE '$MIN_DATE' AND DATE '$PUB_DATE',
                   false);

-- @step rule_bad_amount
INSERT INTO rejected_record
SELECT ocid, 'tender', NULL, 'bad_amount', tender_amount_raw
FROM stg_release
WHERE tender_amount_raw IS NOT NULL AND (tender_amount IS NULL OR tender_amount < 0);
INSERT INTO rejected_record
SELECT ocid, 'award', award_id, 'bad_amount', amount_raw
FROM stg_award
WHERE amount_raw IS NOT NULL AND (amount IS NULL OR amount < 0);
INSERT INTO rejected_record
SELECT ocid, 'contract', contract_id, 'bad_amount', amount_raw
FROM stg_contract
WHERE amount_raw IS NOT NULL AND (try_cast(amount_raw AS DOUBLE) IS NULL
                                  OR try_cast(amount_raw AS DOUBLE) < 0);

-- @step rule_unexpected_currency
-- A currency outside the allowed set, or an amount with no currency at all.
INSERT INTO rejected_record
SELECT ocid, 'award', award_id, 'unexpected_currency', coalesce(currency, '<none>')
FROM stg_award
WHERE (currency IS NOT NULL AND currency NOT IN ($CURRENCIES))
   OR (amount_raw IS NOT NULL AND currency IS NULL);

-- @step rule_dangling_award_ref
-- (records without an ocid are already rejected as missing_required; no knock-on rows)
INSERT INTO rejected_record
SELECT c.ocid, 'contract', c.contract_id, 'dangling_award_ref', coalesce(c.award_id, '<null>')
FROM stg_contract c
WHERE c.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_award a WHERE a.ocid = c.ocid AND a.award_id = c.award_id);

-- @step rule_dangling_party_ref
INSERT INTO rejected_record
SELECT s.ocid, 'award', s.award_id, 'dangling_party_ref', 'supplier ' || coalesce(s.supplier_pid, '<null>')
FROM stg_award_supplier s
WHERE s.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_party p WHERE p.ocid = s.ocid AND p.pid = s.supplier_pid);
INSERT INTO rejected_record
SELECT t.ocid, 'release', NULL, 'dangling_party_ref', 'buyer ' || t.buyer_id
FROM tmp_release_check t
WHERE t.ocid IS NOT NULL AND t.buyer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM stg_party p WHERE p.ocid = t.ocid AND p.pid = t.buyer_id);

-- @step flagged_record
-- D014: award dates outside the window are flagged, not rejected.
CREATE OR REPLACE TABLE flagged_record AS
SELECT ocid, 'award' AS level, award_id AS object_id, 'award_date_outside_window' AS flag,
       award_date_raw AS detail
FROM stg_award
WHERE nullif(trim(award_date_raw), '') IS NULL
   OR NOT coalesce(try_cast(left(award_date_raw, 10) AS DATE)
                   BETWEEN DATE '$MIN_DATE' AND DATE '$PUB_DATE', false);

-- @clean clean_views
CREATE OR REPLACE VIEW rejected_ocid AS SELECT DISTINCT ocid FROM rejected_record WHERE ocid IS NOT NULL;
CREATE OR REPLACE VIEW clean_release AS
  SELECT * FROM stg_release x WHERE x.ocid IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM rejected_ocid r WHERE r.ocid = x.ocid);
CREATE OR REPLACE VIEW clean_party AS
  SELECT * FROM stg_party x WHERE x.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM rejected_ocid r WHERE r.ocid = x.ocid);
CREATE OR REPLACE VIEW clean_award AS
  SELECT * FROM stg_award x WHERE x.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM rejected_ocid r WHERE r.ocid = x.ocid);
CREATE OR REPLACE VIEW clean_award_supplier AS
  SELECT * FROM stg_award_supplier x
  WHERE x.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM rejected_ocid r WHERE r.ocid = x.ocid);
CREATE OR REPLACE VIEW clean_contract AS
  SELECT * FROM stg_contract x WHERE x.ocid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM rejected_ocid r WHERE r.ocid = x.ocid);
