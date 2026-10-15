# Recon output
Run date: 2026-10-15T17:39:46
Input: `data/raw/full.jsonl.gz`
DuckDB: 1.5.6

## q9_party_keys
```sql
-- What fields does a party carry? (to confirm where the name and address live)
SELECT k AS party_key, count(*) AS n
FROM (SELECT unnest(json_keys(party)) AS k FROM r_party)
GROUP BY k ORDER BY n DESC;
```
| party_key | n |
|---|---|
| roles | 1474656 |
| identifier | 1474656 |
| id | 1474655 |
| name | 1474652 |
| address | 1118220 |
| additionalIdentifiers | 557815 |

## q9_identifier_keys
```sql
SELECT k AS identifier_key, count(*) AS n
FROM (SELECT unnest(json_keys(party->'$.identifier')) AS k FROM r_party
      WHERE json_type(party->'$.identifier') = 'OBJECT')
GROUP BY k ORDER BY n DESC;
```
| identifier_key | n |
|---|---|
| scheme | 1474656 |
| id | 1474655 |
| legalName | 1474652 |

## q9_id_format
```sql
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
```
| role | id_class | party_rows | distinct_ids |
|---|---|---|---|
| buyer | 11 digits (legal person) | 552763 | 18816 |
| buyer | other | 4979 | 538 |
| buyer | 16-char CF (natural person) | 20 | 11 |
| supplier | 11 digits (legal person) | 329547 | 61645 |
| supplier | 16-char CF (natural person) | 22668 | 15217 |
| supplier | other | 2716 | 1595 |
| supplier | digits only, shorter than 11 | 750 | 530 |

## q9_id_length_other
```sql
-- Length distribution of ids that fit none of the classes above (counts only).
SELECT role, length(id) AS id_length, count(*) AS party_rows
FROM r_party2
WHERE scheme = 'IT-CF' AND role IN ('buyer', 'supplier')
  AND NOT regexp_matches(id, '^[0-9]{11}$')
  AND NOT regexp_matches(upper(id), '^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
GROUP BY 1, 2 ORDER BY role, party_rows DESC LIMIT 20;
```
| role | id_length | party_rows |
|---|---|---|
| buyer | 14 | 4979 |
| supplier | 11 | 898 |
| supplier | 10 | 491 |
| supplier | 9 | 467 |
| supplier | 12 | 320 |
| supplier | 13 | 318 |
| supplier | 14 | 228 |
| supplier | 8 | 148 |
| supplier | 15 | 142 |
| supplier | 6 | 117 |
| supplier | 7 | 94 |
| supplier | 16 | 79 |
| supplier | 18 | 64 |
| supplier | 4 | 21 |
| supplier | 2 | 20 |
| supplier | 5 | 20 |
| supplier | 17 | 14 |
| supplier | 20 | 9 |
| supplier | 3 | 7 |
| supplier | 1 | 5 |

## q10_distinct_entities
```sql
-- How many distinct identified entities by role, and how many appear in both roles?
WITH b AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'buyer' AND id IS NOT NULL),
     s AS (SELECT DISTINCT id FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL)
SELECT (SELECT count(*) FROM b) AS distinct_buyer_ids,
       (SELECT count(*) FROM s) AS distinct_supplier_ids,
       (SELECT count(*) FROM b JOIN s USING (id)) AS ids_in_both_roles;
```
| distinct_buyer_ids | distinct_supplier_ids | ids_in_both_roles |
|---|---|---|
| 19365 | 78987 | 828 |

## q10_id_to_names
```sql
-- One identifier, how many different name spellings? (supplier role)
WITH g AS (SELECT id, count(DISTINCT name) AS n_names, count(*) AS n_rows
           FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL GROUP BY id)
SELECT CASE WHEN n_names = 1 THEN '1' WHEN n_names = 2 THEN '2'
            WHEN n_names <= 5 THEN '3-5' ELSE '6+' END AS names_per_id,
       count(*) AS ids, sum(n_rows) AS party_rows
FROM g GROUP BY 1 ORDER BY 1;
```
| names_per_id | ids | party_rows |
|---|---|---|
| 1 | 65436 | 130376 |
| 2 | 8563 | 59239 |
| 3-5 | 4313 | 94751 |
| 6+ | 675 | 71315 |

## q10_id_to_names_examples
```sql
-- Legal persons only (11-digit ids): the ten ids with the most distinct name spellings.
SELECT id, count(DISTINCT name) AS n_names, min(name) AS example_a, max(name) AS example_b
FROM r_party2
WHERE role = 'supplier' AND regexp_matches(id, '^[0-9]{11}$')
GROUP BY id ORDER BY n_names DESC LIMIT 10;
```
| id | n_names | example_a | example_b |
|---|---|---|---|
| 00464110352 | 35 | 'COOPERATIVA ITALIANA DI RISTORAZIONE SOCIETA' CO | SOCIETA COOPERATIVA ITALIANA DI RISTORAZIONE SOCIETA COOPERATIVA CIR FOOD S.C. |
| 04876970486 | 34 | 3.CO&SO CONSORZIO PER LA COOPERAZIONE E LA SOLIDARIET'-CONSORZIO DI COOPERATIVE SOCIALI-SOCIET' COOPERATIVA SOCIALE | SOCIETÀ COOPERATIVA CO&SO |
| 00311310379 | 27 | 00311310379 | CAMST SOCIETA' COOPERATIVA A.R.L. |
| 00488410010 | 24 | TEELECOM | TIM SPA EX TELECOM ITALIA SPA |
| 11264670156 | 23 | ABBOT MEDICAL | STJUDE MEDICAL ITALIA |
| 02884150588 | 23 | C.N.S. | CONSORZIO NAZIONALE SERVIZI SOC. COOP. |
| 00310180351 | 22 | COOP SERVICE  SOC. COOP. PER AZIONI | COOPSERVICE SOCIETÀ COOPERATIVA PER AZIONI |
| 00818570012 | 22 | 00818570012 | UNIPOLSAI SPA |
| 01286700487 | 22 | L. MOLTENI & C. DEI F.LLI ALITTI S.P.A. | MOLTENI L. & C. DEI FRATELLI ALITTI |
| 03907010585 | 21 | 03907010585 | AZIENDE CHIMICHE RIUNITE ANGELINI FRANCESCO SPA |

## q10_name_to_ids
```sql
-- One normalised name, how many different identifiers? (supplier role; counts only)
WITH g AS (SELECT name, count(DISTINCT id) AS n_ids, count(*) AS n_rows
           FROM r_party2 WHERE role = 'supplier' AND id IS NOT NULL AND name IS NOT NULL GROUP BY name)
SELECT CASE WHEN n_ids = 1 THEN '1' WHEN n_ids = 2 THEN '2'
            WHEN n_ids <= 5 THEN '3-5' ELSE '6+' END AS ids_per_name,
       count(*) AS names, sum(n_rows) AS party_rows
FROM g GROUP BY 1 ORDER BY 1;
```
| ids_per_name | names | party_rows |
|---|---|---|
| 1 | 96005 | 295922 |
| 2 | 2898 | 45452 |
| 3-5 | 307 | 13728 |
| 6+ | 16 | 576 |

## q11_rti_names
```sql
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
```
| name_pattern | supplier_rows | distinct_ids |
|---|---|---|
| none of the above | 349125 | 78189 |
| consorzio | 6253 | 830 |
| RTI / ATI | 259 | 142 |
| raggruppamento | 29 | 11 |
| GEIE / rete | 15 | 8 |

## q11_suppliers_per_award
```sql
-- How many suppliers are listed on one award? (more than one hints at how groupings are encoded)
SELECT coalesce(json_array_length(award->'$.suppliers'), 0) AS n_suppliers, count(*) AS awards
FROM r_award GROUP BY 1 ORDER BY 1;
```
| n_suppliers | awards |
|---|---|
| 0 | 870 |
| 1 | 293006 |
| 2 | 15439 |
| 3 | 6424 |
| 4 | 3709 |
| 5 | 1994 |
| 6 | 908 |
| 7 | 648 |
| 8 | 343 |
| 9 | 142 |
| 10 | 126 |
| 11 | 77 |
| 12 | 41 |
| 13 | 39 |
| 14 | 50 |
| 15 | 16 |
| 16 | 39 |
| 17 | 21 |
| 18 | 17 |
| 19 | 10 |
| 20 | 29 |
| 21 | 2 |
| 23 | 3 |
| 24 | 2 |
| 25 | 4 |
| 26 | 34 |
| 27 | 6 |
| 29 | 2 |
| 30 | 2 |
| 32 | 2 |
| 33 | 2 |
| 34 | 1 |
| 35 | 3 |
| 37 | 4 |
| 38 | 8 |
| 41 | 2 |
| 43 | 1 |
| 45 | 2 |
| 47 | 1 |
| 49 | 1 |

## q12_award_value_buckets
```sql
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
```
| bucket | awards | total_eur | pct_of_total_value |
|---|---|---|---|
| 0 null | 171 | None | None |
| 1 under 40k | 44576 | 771302627.0 | 0.22 |
| 2 40k to 1M | 248260 | 48652416220.0 | 13.59 |
| 3 1M to 10M | 27507 | 77078104383.0 | 21.52 |
| 4 10M to 100M | 3284 | 80298161506.0 | 22.42 |
| 5 100M to 1bn | 210 | 46314976699.0 | 12.93 |
| 6 1bn and above | 22 | 105004619811.0 | 29.32 |

## q12_award_outliers_context
```sql
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
```
| ocid | n_awards_in_process | tender_amount | method | title |
|---|---|---|---|---|
| ocds-hu01ve-8206857 | 3 | 157942658.69 | None | None |
| ocds-hu01ve-7158806 | 5 | 10268728.0 | None | None |
| ocds-hu01ve-7176845 | 1 | 7327602077.0 | None | None |
| ocds-hu01ve-8422821 | 1 | 723300000.0 | None | None |
| ocds-hu01ve-8581608 | 1 | 6105000.0 | None | None |
| ocds-hu01ve-8586450 | 1 | 125827251.02 | None | None |
| ocds-hu01ve-8664938 | 1 | 4525000000.0 | None | None |
| ocds-hu01ve-8682745 | 1 | 34511040.0 | None | None |
| ocds-hu01ve-7483943 | 35 | 19517500.0 | None | None |
| ocds-hu01ve-7635795 | 1 | 1828634125.0 | None | None |

## q13_contract_values
```sql
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
```
| contracts | with_contract_value | equal_to_award | differs_from_award |
|---|---|---|---|
| 185259 | 0 | 0 | 0 |

## q14_supplier_count_gap
```sql
-- The spec states 390,526 suppliers. Which count does that match?
SELECT (SELECT count(*) FROM r_party2 WHERE role = 'supplier') AS supplier_party_rows,
       (SELECT count(DISTINCT id) FROM r_party2 WHERE role = 'supplier') AS distinct_supplier_ids,
       (SELECT count(DISTINCT (ocid, name)) FROM r_party2 WHERE role = 'supplier') AS distinct_ocid_name,
       (SELECT sum(coalesce(json_array_length(award->'$.suppliers'), 0)) FROM r_award) AS award_supplier_refs;
```
| supplier_party_rows | distinct_supplier_ids | distinct_ocid_name | award_supplier_refs |
|---|---|---|---|
| 355681 | 78987 | 355563 | 390526 |

## q15_method_coding
```sql
-- Procedure mix depends on procurementMethod: populated, and which values?
SELECT coalesce(doc->>'$.tender.procurementMethod', '<null>') AS method,
       count(*) AS tenders,
       round(100.0 * count(*) / (SELECT count(*) FROM raw WHERE (doc->'$.tender') IS NOT NULL), 2) AS pct
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY tenders DESC LIMIT 15;
```
| method | tenders | pct |
|---|---|---|
| <null> | 562862 | 100.0 |

## q15_method_details
```sql
SELECT coalesce(left(doc->>'$.tender.procurementMethodDetails', 80), '<null>') AS method_details,
       count(*) AS tenders
FROM raw WHERE (doc->'$.tender') IS NOT NULL
GROUP BY 1 ORDER BY tenders DESC LIMIT 20;
```
| method_details | tenders |
|---|---|
| COD:24 ; TITLE:AFFIDAMENTO DIRETTO | 170521 |
| COD:27 ; TITLE:AFFIDAMENTO DIRETTO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE | 167278 |
| COD:34 ; TITLE:PROCEDURA NEGOZIATA PER AFFIDAMENTI SOTTO SOGLIA | 67329 |
| COD:4 ; TITLE:PROCEDURA NEGOZIATA SENZA PREVIA PUBBLICAZIONE | 57703 |
| COD:1 ; TITLE:PROCEDURA APERTA | 43531 |
| COD:6 ; TITLE:PROCEDURA NEGOZIATA SENZA PREVIA INDIZIONE DI GARA (SETTORI SPECIA | 16143 |
| COD:8 ; TITLE:AFFIDAMENTO IN ECONOMIA - COTTIMO FIDUCIARIO | 10795 |
| COD:28 ; TITLE:CONFRONTO COMPETITIVO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE | 5161 |
| COD:14 ; TITLE:PROCEDURA SELETTIVA EX ART. 238 C.7, D.LGS. 163/2006 | 4948 |
| COD:2 ; TITLE:PROCEDURA RISTRETTA | 4761 |
| COD:114 ; TITLE:PROCEDURA NEGOZIATA DERIVANTE DA AVVISI CON CUI SI INDICE UNA GA | 4432 |
| COD:23 ; TITLE:PROCEDURA NEGOZIATA CON PREVIA INDIZIONE DI GARA (SETTORI SPECIAL | 2510 |
| COD:32 ; TITLE:AFFIDAMENTO DIRETTO PER VARIANTE SUPERIORE AL 20% DELL'IMPORTO CO | 1148 |
| COD:7 ; TITLE:SISTEMA DINAMICO DI ACQUISIZIONE | 1117 |
| COD:3 ; TITLE:PROCEDURA NEGOZIATA PREVIA PUBBLICAZIONE | 922 |
| COD:25 ; TITLE:AFFIDAMENTO DIRETTO A SOCIETA' IN HOUSE | 878 |
| COD:38 ; TITLE:PROCEDURA COMPETITIVA CON NEGOZIAZIONE | 756 |
| COD:12 ; TITLE:AFFIDAMENTO DIRETTO EX ART.5 DELLA LEGGE N.381/91 | 578 |
| COD:26 ; TITLE:AFFIDAMENTO DIRETTO A SOCIETA' RAGGRUPPATE/CONSORZIATE O CONTROLL | 500 |
| COD:40 ; TITLE:AFFIDAMENTO DIRETTO PER MODIFICHE CONTRATTUALI O VARIANTI PER LE  | 413 |

## q16_cpv_populatedness
```sql
-- cpv_division in fact_award needs tender.items[].classification.
WITH t AS (SELECT doc->'$.tender.items' AS items FROM raw WHERE (doc->'$.tender') IS NOT NULL)
SELECT count(*) AS tenders,
       count(*) FILTER (WHERE coalesce(json_array_length(items), 0) > 0) AS with_items,
       count(*) FILTER (WHERE (items->'$[0].classification.id') IS NOT NULL) AS with_classification
FROM t;
```
| tenders | with_items | with_classification |
|---|---|---|
| 562862 | 562862 | 562764 |

## q16_classification_schemes
```sql
SELECT coalesce(it->>'$.classification.scheme', '<null>') AS scheme, count(*) AS items
FROM (SELECT unnest(from_json(doc->'$.tender.items', '["JSON"]')) AS it FROM raw)
GROUP BY 1 ORDER BY items DESC LIMIT 10;
```
| scheme | items |
|---|---|
| CPV | 698350 |

## q17_buyer_region
```sql
-- region in fact_award comes from the buyer's address.
SELECT count(*) AS buyer_rows, count(region) AS with_region,
       round(100.0 * count(region) / count(*), 2) AS pct_with_region
FROM r_party2 WHERE role = 'buyer';
```
| buyer_rows | with_region | pct_with_region |
|---|---|---|
| 557762 | 0 | 0.0 |
