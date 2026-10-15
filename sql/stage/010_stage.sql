-- Ticket A3: raw OCDS lines into typed staging tables. Nothing is dropped or corrected here;
-- values that do not parse stay NULL and the raw text is kept next to them, so Gate 1 (A4)
-- can count and name every defect. Blocks start with "-- @step <name>".
-- $RAW_FILE is substituted by src/appalti/stage.py. A step containing $CHUNK is run once per
-- slice of the lines (hash of ocid modulo N): the first slice creates the table, the others
-- INSERT into it. This keeps the unnested JSON small enough for a 16 GB laptop.

-- @step raw
CREATE OR REPLACE TABLE raw AS
SELECT line::JSON AS doc
FROM read_csv('$RAW_FILE', columns={'line': 'VARCHAR'}, delim=E'\x07',
              quote='', escape='', header=false, max_line_size=104857600);

-- @step stg_release
-- One row per line. Stub lines (no tender) are kept and flagged.
CREATE OR REPLACE TABLE stg_release AS
SELECT doc->>'$.ocid' AS ocid,
       doc->>'$.date' AS release_date_raw,
       try_cast(left(doc->>'$.date', 4) AS INTEGER) AS release_year,
       coalesce(json_type(doc->'$.tender') = 'OBJECT', false) AS has_tender,
       doc->>'$.tender.tenderPeriod.startDate' AS tender_start_raw,
       try_cast(left(doc->>'$.tender.tenderPeriod.startDate', 4) AS INTEGER) AS tender_start_year,
       doc->>'$.tender.value.amount' AS tender_amount_raw,
       try_cast(doc->>'$.tender.value.amount' AS DOUBLE) AS tender_amount,
       doc->>'$.tender.value.currency' AS tender_currency,
       try_cast(doc->>'$.tender.numberOfTenderers' AS INTEGER) AS number_of_tenderers,
       doc->>'$.tender.procurementMethod' AS procurement_method,
       doc->>'$.tender.procurementMethodDetails' AS procurement_method_details,
       try_cast(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1)
                AS INTEGER) AS procedure_code,
       left(doc->>'$.tender.items[0].classification.id', 2) AS cpv_division,
       coalesce(json_array_length(doc->'$.parties'), 0) AS n_parties,
       coalesce(json_array_length(doc->'$.awards'), 0) AS n_awards,
       coalesce(json_array_length(doc->'$.contracts'), 0) AS n_contracts,
       coalesce(json_array_length(doc->'$.tender.milestones'), 0) AS n_milestones_tender
FROM raw;

-- @step stg_party
-- Only the fields we need are pulled out as typed values; the full party JSON is never copied.
CREATE OR REPLACE TABLE stg_party AS
SELECT ocid,
       p.id AS pid,
       coalesce(len(p.roles), 0) AS n_roles,
       p.roles[1] AS role,
       p.identifier.scheme AS id_scheme,
       nullif(trim(p.identifier.id), '') AS id_raw,
       upper(trim(coalesce(p.name, p.identifier.legalName))) AS name,
       nullif(trim(p.address.postalCode), '') AS postal_code
FROM (SELECT ocid, unnest(parties) AS p
      FROM (SELECT doc->>'$.ocid' AS ocid,
                   from_json(doc->'$.parties',
                     '[{"id":"VARCHAR","name":"VARCHAR","roles":["VARCHAR"],
                        "identifier":{"scheme":"VARCHAR","id":"VARCHAR","legalName":"VARCHAR"},
                        "address":{"postalCode":"VARCHAR"}}]') AS parties
            FROM raw WHERE $CHUNK));

-- @step stg_award
CREATE OR REPLACE TABLE stg_award AS
SELECT ocid,
       a.id AS award_id,
       a.date AS award_date_raw,
       try_cast(left(a.date, 4) AS INTEGER) AS award_year,
       a.value.amount AS amount_raw,
       try_cast(a.value.amount AS DOUBLE) AS amount,
       a.value.currency AS currency,
       coalesce(len(a.suppliers), 0) AS n_suppliers
FROM (SELECT ocid, unnest(awards) AS a
      FROM (SELECT doc->>'$.ocid' AS ocid,
                   from_json(doc->'$.awards',
                     '[{"id":"VARCHAR","date":"VARCHAR",
                        "value":{"amount":"VARCHAR","currency":"VARCHAR"},
                        "suppliers":[{"id":"VARCHAR"}]}]') AS awards
            FROM raw WHERE $CHUNK));

-- @step stg_award_supplier
-- One row per supplier reference on an award (the bridge D021 needs).
CREATE OR REPLACE TABLE stg_award_supplier AS
SELECT ocid, a.id AS award_id, unnest(a.suppliers).id AS supplier_pid
FROM (SELECT ocid, unnest(awards) AS a
      FROM (SELECT doc->>'$.ocid' AS ocid,
                   from_json(doc->'$.awards',
                     '[{"id":"VARCHAR","suppliers":[{"id":"VARCHAR"}]}]') AS awards
            FROM raw WHERE $CHUNK));

-- @step stg_contract
CREATE OR REPLACE TABLE stg_contract AS
SELECT ocid,
       c.id AS contract_id,
       c.awardID AS award_id,
       c.value.amount AS amount_raw,
       coalesce(json_array_length(c.amendments), 0) AS n_amendments,
       coalesce(json_array_length(c.implementation.milestones), 0) AS n_milestones
FROM (SELECT ocid, unnest(contracts) AS c
      FROM (SELECT doc->>'$.ocid' AS ocid,
                   from_json(doc->'$.contracts',
                     '[{"id":"VARCHAR","awardID":"VARCHAR","value":{"amount":"VARCHAR"},
                        "amendments":"JSON","implementation":{"milestones":"JSON"}}]') AS contracts
            FROM raw WHERE $CHUNK));
