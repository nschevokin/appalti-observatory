-- Ticket B1/B3 as revised by D020: the entity key is the normalised IT-CF identifier.
-- Reads the clean_* views (Gate 1 passed). Placeholders are filled in by entities.py.
-- entity_alias(key, merged_key) is created by entities.py before this file runs; it is empty
-- unless an audited merge rule was chosen (audit.toml, apply_rules).

-- @step ids11
-- The 11-digit supplier ids, the only ids a short digit-only id may be padded to (D027).
CREATE OR REPLACE TABLE tmp_ids11 AS
SELECT DISTINCT id_raw FROM clean_party
WHERE role = 'supplier' AND regexp_matches(id_raw, '^[0-9]{11}$');

-- @step party_key
-- One row per buyer or supplier party. key is the id as normalised (before any audited merge),
-- entity_key the key after the merge. Rows with neither an id nor a name get no key.
CREATE OR REPLACE TABLE party_key AS
WITH base AS (
  SELECT p.ocid, p.pid, p.role, p.name, p.postal_code, p.id_raw,
         t.id_raw AS padded_from
  FROM clean_party p
  LEFT JOIN tmp_ids11 t
    ON regexp_matches(p.id_raw, '^[0-9]{1,10}$') AND t.id_raw = lpad(p.id_raw, 11, '0')
  WHERE p.role IN ('buyer', 'supplier')),
keyed AS (
  SELECT *,
    CASE WHEN id_raw IS NOT NULL AND padded_from IS NOT NULL THEN 'IT-CF:' || padded_from
         WHEN id_raw IS NOT NULL THEN 'IT-CF:' || upper(id_raw)
         WHEN name IS NOT NULL THEN 'NAME:' || name END AS key,
    CASE WHEN id_raw IS NOT NULL AND padded_from IS NOT NULL THEN 'identifier_padded'
         WHEN id_raw IS NOT NULL THEN 'identifier'
         WHEN name IS NOT NULL THEN 'name' END AS key_method
  FROM base)
SELECT k.ocid, k.pid, k.role, k.name, k.postal_code, k.key, k.key_method,
       coalesce(a.merged_key, k.key) AS entity_key
FROM keyed k LEFT JOIN entity_alias a ON a.key = k.key;

-- @step entity
-- Canonical name: the most frequent spelling that is not just the id; ties break alphabetically.
-- entity_id is a hash of the key, so the same input always gives the same ids.
CREATE OR REPLACE TABLE entity AS
WITH names AS (
  SELECT entity_key, name, count(*) AS n,
         row_number() OVER (PARTITION BY entity_key ORDER BY count(*) DESC, name) AS rk
  FROM party_key
  WHERE name IS NOT NULL AND name <> replace(entity_key, 'IT-CF:', '')
  GROUP BY entity_key, name),
agg AS (
  SELECT entity_key,
         count(*) AS n_rows,
         bool_or(role = 'buyer') AS is_buyer,
         bool_or(role = 'supplier') AS is_supplier,
         count(DISTINCT key) AS n_source_keys,
         bool_or(key_method <> 'name') AS has_identifier
  FROM party_key WHERE entity_key IS NOT NULL GROUP BY entity_key)
SELECT 'E' || substr(sha256(a.entity_key), 1, 16) AS entity_id,
       a.entity_key,
       coalesce(n.name, replace(a.entity_key, 'IT-CF:', '')) AS canonical_name,
       CASE WHEN a.has_identifier THEN 'IT-CF' END AS identifier_scheme,
       CASE WHEN a.has_identifier THEN replace(a.entity_key, 'IT-CF:', '') END AS identifier_id,
       CASE WHEN a.is_buyer AND a.is_supplier THEN 'both'
            WHEN a.is_buyer THEN 'buyer' ELSE 'supplier' END AS kind,
       CASE WHEN a.n_source_keys > 1 THEN 'name_match'
            WHEN a.has_identifier THEN 'identifier'
            WHEN a.n_rows > 1 THEN 'name_match' ELSE 'singleton' END AS method,
       CAST(NULL AS DOUBLE) AS confidence
FROM agg a LEFT JOIN names n ON n.entity_key = a.entity_key AND n.rk = 1;
