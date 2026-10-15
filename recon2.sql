-- Second-pass reconnaissance (ticket A1b). Written after the first pass, so it is explicitly
-- NOT part of the pre-registered rules. Same block format as recon.sql.
-- PRIVACY: the recon output is committed to a public repository. These queries therefore
-- never print names or ids of anyone who might be a natural person: only counts, buckets,
-- and (where names appear) only for 11-digit identifiers, i.e. legal persons.
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

-- One row per party with its single role, scheme, identifier and upper-cased name.
CREATE OR REPLACE VIEW r_party2 AS
SELECT ocid,
       party->>'$.id' AS pid,
       from_json(party->'$.roles', '["VARCHAR"]')[1] AS role,
       party->>'$.identifier.scheme' AS scheme,
       nullif(trim(party->>'$.identifier.id'), '') AS id,
       upper(trim(coalesce(party->>'$.name', party->>'$.identifier.legalName'))) AS name,
       party->>'$.address.region' AS region
FROM r_party;

-- @query q9_party_keys
-- What fields does a party carry? (to confirm where the name and address live)
SELECT k AS party_key, count(*) AS n
FROM (SELECT unnest(json_keys(party)) AS k FROM r_party)
GROUP BY k ORDER BY n DESC;

-- @query q9_identifier_keys
SELECT k AS identifier_key, count(*) AS n
FROM (SELECT unnest(json_keys(party->'$.identifier')) AS k FROM r_party
      WHERE json_type(party->'$.identifier') = 'OBJECT')
GROUP BY k ORDER BY n DESC;

-- @query q9_id_format
-- Identifier shape by role: 11 digits = legal person; 16 characters = natural person (D009).
SELECT role,
       CASE WHEN regexp_matches(id, '^[0-9]{11}$') THEN '11 digits (legal person)'
            WHEN regexp_matches(upper(id), '^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$') THEN '16-char CF (natural person)'
            WHEN regexp_matches(id, '^[0-9]{1,10}$') THEN 'digits only, shorter than 11'
            ELSE 'other' END AS id_class,
       count(*) AS party_rows,
       count(DISTINCT id) AS distinct_ids
FROM r_party2 WHERE scheme = 'IT-CF' AND role IN ('buyer', 'supplier')
GROUP BY 1, 2 ORDER BY role, party_rows DESC;

-- @query q9_id_length_other
-- Length distribution of ids that fit none of the classes above (counts only).
SELECT role, length(id) AS id_length, count(*) AS party_rows
FROM r_party2
WHERE scheme = 'IT-CF' AND role IN ('buyer', 'supplier')
  AND NOT regexp_matches(id, '^[0-9]{11}$')
  AND NOT regexp_matches(upper(id), '^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
GROUP BY 1, 2 ORDER BY role, party_rows DESC LIMIT 20;

-- @query q10_distinct_entities
-- How many distinct identified entities by role, and how many appear in both roles?
WITH b AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'buyer' AND id IS NOT NULL),
     s AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL)
SELECT (SELECT count(*) FROM b) AS distinct_buyer_ids,
       (SELECT count(*) FROM s) AS distinct_supplier_ids,
       (SELECT count(*) FROM b JOIN s USING (id)) AS ids_in_both_roles;

-- @query q10_id_to_names
-- One identifier, how many different name spellings? (supplier role)
WITH g AS (SELECT id, count(DISTINCT name) AS n_names, count(*) AS n_rows
           FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL GROUP BY id)
SELECT CASE WHEN n_names = 1 THEN '1' WHEN n_names = 2 THEN '2'
            WHEN n_names <= 5 THEN '3-5' ELSE '6+' END AS names_per_id,
       count(*) AS ids, sum(n_rows) AS party_rows
FROM g GROUP BY 1 ORDER BY 1;

-- @query q10_id_to_names_examples
-- Legal persons only (11-digit ids): the ten ids with the most distinct name spellings.
SELECT id, count(DISTINCT name) AS n_names, min(name) AS example_a, max(name) AS example_b
FROM r_party2
WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{11}$')
GROUP BY id ORDER BY n_names DESC LIMIT 10;

-- @query q10_name_to_ids
-- One normalised name, how many different identifiers? (supplier role; counts only)
WITH g AS (SELECT name, count(DISTINCT id) AS n_ids, count(*) AS n_rows
           FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL AND name IS NOT NULL GROUP BY name)
SELECT CASE WHEN n_ids = 1 THEN '1' WHEN n_ids = 2 THEN '2'
            WHEN n_ids <= 5 THEN '3-5' ELSE '6+' END AS ids_per_name,
       count(*) AS names, sum(n_rows) AS party_rows
FROM g GROUP BY 1 ORDER BY 1;

-- @query q11_rti_names
-- Do temporary groupings and consortia show up in supplier names? (counts only, D006)
SELECT CASE
         WHEN regexp_matches(name, '\b(RTI|R\.T\.I\.?|ATI|A\.T\.I\.?)\b') THEN 'RTI / ATI'
         WHEN name LIKE '%RAGGRUPPAMENTO%' OR name LIKE '%RAGG. TEMP%' THEN 'raggruppamento'
         WHEN name LIKE '%CONSORZIO%' OR name LIKE '%CONSORZIATE%' THEN 'consorzio'
         WHEN name LIKE '%GEIE%' OR name LIKE '%RETE DI IMPRESE%' THEN 'GEIE / rete'
         ELSE 'none of the above' END AS name_pattern,
       count(*) AS supplier_rows, count(DISTINCT id) AS distinct_ids
FROM r_party2 WHERE role = 'supplier'
GROUP BY 1 ORDER BY supplier_rows DESC;

-- @query q11_suppliers_per_award
-- How many suppliers are listed on one award? (more than one hints at how groupings are encoded)
SELECT coalesce(json_array_length(award->'$.suppliers'), 0) AS n_suppliers, count(*) AS awards
FROM r_award GROUP BY 1 ORDER BY 1;

-- @query q12_award_value_buckets
-- Where does the money sit? Awards and summed value by amount bucket.
WITH a AS (SELECT try_cast(award->>'$.value.amount' AS DOUBLE) AS amt FROM r_award)
SELECT CASE WHEN amt IS NULL THEN '0 null'
            WHEN amt < 40000 THEN '1 under 40k'
            WHEN amt < 1000000 THEN '2 40k to 1M'
            WHEN amt < 10000000 THEN '3 1M to 10M'
            WHEN amt < 100000000 THEN '4 10M to 100M'
            WHEN amt < 1000000000 THEN '5 100M to 1bn'
            ELSE '6 1bn and above' END AS bucket,
       count(*) AS awards,
       round(sum(amt)) AS total_eur,
       round(100.0 * sum(amt) / (SELECT sum(amt) FROM a), 2) AS pct_of_total_value
FROM a GROUP BY 1 ORDER BY 1;

-- @query q12_award_outliers_context
-- The ten largest awards in context: tender value, method and title (awards, not entities).
-- No join: joining awards to the raw documents ran out of memory twice. The ten ocids below
-- are the ten largest awards from q5_amounts_largest in recon_output.md (2026-10-15 run);
-- the dataset is frozen, so the list is stable. Award amounts are in that earlier table.
SELECT doc->>'$.ocid' AS ocid,
       json_array_length(doc->'$.awards') AS n_awards_in_process,
       try_cast(doc->>'$.tender.value.amount' AS DOUBLE) AS tender_amount,
       doc->>'$.tender.procurementMethod' AS method,
       left(doc->>'$.tender.title', 100) AS title
FROM raw
WHERE (doc->>'$.ocid') IN ('ocds-hu01ve-8682745', 'ocds-hu01ve-8206857', 'ocds-hu01ve-7176845',
                           'ocds-hu01ve-8664938', 'ocds-hu01ve-8586450', 'ocds-hu01ve-8581608',
                           'ocds-hu01ve-7483943', 'ocds-hu01ve-8422821', 'ocds-hu01ve-7158806',
                           'ocds-hu01ve-7635795');

-- @query q13_contract_values
-- Do contracts carry a value, and does it equal the award value?
WITH c AS (SELECT ocid, contract->>'$.awardID' AS award_id,
                  try_cast(contract->>'$.value.amount' AS DOUBLE) AS c_amt FROM r_contract),
     a AS (SELECT ocid, award->>'$.id' AS award_id,
                  try_cast(award->>'$.value.amount' AS DOUBLE) AS a_amt FROM r_award)
SELECT count(*) AS contracts,
       count(c.c_amt) AS with_contract_value,
       count(*) FILTER (WHERE c.c_amt = a.a_amt) AS equal_to_award,
       count(*) FILTER (WHERE c.c_amt <> a.a_amt) AS differs_from_award
FROM c LEFT JOIN a ON c.ocid = a.ocid AND c.award_id = a.award_id;

-- @query q14_supplier_count_gap
-- The spec states 390,526 suppliers. Which count does that match?
SELECT (SELECT count(*) FROM r_party2 WHERE role = 'supplier') AS supplier_party_rows,
       (SELECT count(DISTINCT id) FROM r_party2 WHERE role = 'supplier') AS distinct_supplier_ids,
       (SELECT count(DISTINCT (ocid, name)) FROM r_party2 WHERE role = 'supplier') AS distinct_ocid_name,
       (SELECT sum(coalesce(json_array_length(award->'$.suppliers'), 0)) FROM r_award) AS award_supplier_refs;

-- @query q15_method_coding
-- Procedure mix depends on procurementMethod: populated, and which values?
SELECT coalesce(doc->>'$.tender.procurementMethod', '<null>') AS method,
       count(*) AS tenders,
       round(100.0 * count(*) / (SELECT count(*) FROM raw WHERE (doc->'$.tender') IS NOT NULL), 2) AS pct
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY tenders DESC LIMIT 15;

-- @query q15_method_details
SELECT coalesce(left(doc->>'$.tender.procurementMethodDetails', 80), '<null>') AS method_details,
       count(*) AS tenders
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY tenders DESC LIMIT 20;

-- @query q16_cpv_populatedness
-- cpv_division in fact_award needs tender.items[].classification.
WITH t AS (SELECT doc->'$.tender.items' AS items FROM raw WHERE (doc->'$.tender') IS NOT NULL)
SELECT count(*) AS tenders,
       count(*) FILTER (WHERE coalesce(json_array_length(items), 0) > 0) AS with_items,
       count(*) FILTER (WHERE (items->'$[0].classification.id') IS NOT NULL) AS with_classification
FROM t;

-- @query q16_classification_schemes
SELECT coalesce(it->>'$.classification.scheme', '<null>') AS scheme, count(*) AS items
FROM (SELECT unnest(from_json(doc->'$.tender.items', '["JSON"]')) AS it FROM raw)
GROUP BY 1 ORDER BY items DESC LIMIT 10;

-- @query q17_buyer_region
-- region in fact_award comes from the buyer's address.
SELECT count(*) AS buyer_rows, count(region) AS with_region,
       round(100.0 * count(region) / count(*), 2) AS pct_with_region
FROM r_party2 WHERE role = 'buyer';
