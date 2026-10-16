# Recon output
Run date: 2026-10-16T14:11:10+00:00
Input: `data/raw/full.jsonl.gz`
DuckDB: 1.5.6

## q30_procedure_codes
```sql
-- Every COD value with its title and how many tenders carry it.
WITH t AS (
  SELECT try_cast(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'COD:([0-9]+)', 1)
                  AS INTEGER) AS cod,
         trim(regexp_extract(doc->>'$.tender.procurementMethodDetails', 'TITLE:(.*)$', 1)) AS title
  FROM raw WHERE (doc->'$.tender') IS NOT NULL)
SELECT cod, title, count(*) AS tenders,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
FROM t GROUP BY 1, 2 ORDER BY 3 DESC;
```
| cod | title | tenders | pct |
|---|---|---|---|
| 24 | AFFIDAMENTO DIRETTO | 170521 | 30.3 |
| 27 | AFFIDAMENTO DIRETTO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE | 167278 | 29.72 |
| 34 | PROCEDURA NEGOZIATA PER AFFIDAMENTI SOTTO SOGLIA | 67329 | 11.96 |
| 4 | PROCEDURA NEGOZIATA SENZA PREVIA PUBBLICAZIONE | 57703 | 10.25 |
| 1 | PROCEDURA APERTA | 43531 | 7.73 |
| 6 | PROCEDURA NEGOZIATA SENZA PREVIA INDIZIONE DI GARA (SETTORI SPECIALI) | 16143 | 2.87 |
| 8 | AFFIDAMENTO IN ECONOMIA - COTTIMO FIDUCIARIO | 10795 | 1.92 |
| 28 | CONFRONTO COMPETITIVO IN ADESIONE AD ACCORDO QUADRO/CONVENZIONE | 5161 | 0.92 |
| 14 | PROCEDURA SELETTIVA EX ART. 238 C.7, D.LGS. 163/2006 | 4948 | 0.88 |
| 2 | PROCEDURA RISTRETTA | 4761 | 0.85 |
| 114 | PROCEDURA NEGOZIATA DERIVANTE DA AVVISI CON CUI SI INDICE UNA GARA | 4432 | 0.79 |
| 23 | PROCEDURA NEGOZIATA CON PREVIA INDIZIONE DI GARA (SETTORI SPECIALI) | 2510 | 0.45 |
| 32 | AFFIDAMENTO DIRETTO PER VARIANTE SUPERIORE AL 20% DELL'IMPORTO CONTRATTUALE | 1148 | 0.2 |
| 7 | SISTEMA DINAMICO DI ACQUISIZIONE | 1117 | 0.2 |
| 3 | PROCEDURA NEGOZIATA PREVIA PUBBLICAZIONE | 922 | 0.16 |
| 25 | AFFIDAMENTO DIRETTO A SOCIETA' IN HOUSE | 878 | 0.16 |
| 38 | PROCEDURA COMPETITIVA CON NEGOZIAZIONE | 756 | 0.13 |
| 12 | AFFIDAMENTO DIRETTO EX ART.5 DELLA LEGGE N.381/91 | 578 | 0.1 |
| 26 | AFFIDAMENTO DIRETTO A SOCIETA' RAGGRUPPATE/CONSORZIATE O CONTROLLATE NELLE CONCESSIONI E NEI PARTENARIATI | 500 | 0.09 |
| 40 | AFFIDAMENTO DIRETTO PER MODIFICHE CONTRATTUALI O VARIANTI PER LE QUALI È NECESSARIA UNA NUOVA PROCEDURA DI AFFIDAMENTO | 413 | 0.07 |
| 22 | PROCEDURA RISTRETTA DERIVANTE DA AVVISI CON CUI SI INDICE LA GARA | 394 | 0.07 |
| 33 | AFFIDAMENTO RISERVATO | 348 | 0.06 |
| 37 | AFFIDAMENTO DIRETTO PER LAVORI, SERVIZI O FORNITURE SUPPLEMENTARI | 302 | 0.05 |
| 5 | DIALOGO COMPETITIVO | 120 | 0.02 |
| 30 | PROCEDURA RISTRETTA SEMPLIFICATA | 70 | 0.01 |
| 29 | PROCEDURA AI SENSI DEI REGOLAMENTI DEGLI ORGANI COSTITUZIONALI | 54 | 0.01 |
| 22 | PROCEDURA RISTRETTA DERIVANTE DA AVVISI CON CUI SI INDICE UNA GARA | 49 | 0.01 |
| 35 | PROCEDURA ART.16 COMMA 2-BIS DPR 380/2001 PER OPERE URBANIZZAZIONE A SCOMPUTO PRIMARIE SOTTO SOGLIA COMUNITARIA | 35 | 0.01 |
| 36 | PARTERNARIATO PER L’INNOVAZIONE | 31 | 0.01 |
| 16 | ACCORDO QUADRO | 23 | 0.0 |
| 15 | PROCEDURA NEGOZIATA | 12 | 0.0 |

## q31_procedure_codes_in_awards
```sql
-- Same, on awards that made it into fact_award (the population the indicators use).
SELECT procedure_code AS cod, count(*) AS awards,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct,
       round(sum(amount_eur) / 1e9, 2) AS value_bn_eur
FROM fact_award GROUP BY 1 ORDER BY 2 DESC;
```
| cod | awards | pct | value_bn_eur |
|---|---|---|---|
| 27 | 80275 | 24.85 | 73.56 |
| 24 | 70233 | 21.75 | 11.11 |
| 1 | 45299 | 14.03 | 132.38 |
| 34 | 41738 | 12.92 | 10.83 |
| 4 | 40660 | 12.59 | 59.62 |
| 6 | 9627 | 2.98 | 12.53 |
| 7 | 8555 | 2.65 | 13.03 |
| 2 | 7609 | 2.36 | 18.92 |
| 8 | 5289 | 1.64 | 0.66 |
| 14 | 3723 | 1.15 | 1.22 |
| 114 | 3038 | 0.94 | 4.11 |
| 28 | 2004 | 0.62 | 1.82 |
| 23 | 1708 | 0.53 | 11.17 |
| 3 | 648 | 0.2 | 2.26 |
| 22 | 418 | 0.13 | 1.55 |
| 38 | 413 | 0.13 | 0.26 |
| 40 | 328 | 0.1 | 0.13 |
| 25 | 297 | 0.09 | 0.59 |
| 26 | 247 | 0.08 | 0.51 |
| 12 | 209 | 0.06 | 0.07 |
| 33 | 191 | 0.06 | 0.07 |
| 32 | 182 | 0.06 | 0.2 |
| 37 | 140 | 0.04 | 0.04 |
| 5 | 42 | 0.01 | 0.49 |
| 30 | 40 | 0.01 | 0.01 |
| 16 | 36 | 0.01 | 0.03 |
| 35 | 11 | 0.0 | 0.01 |
| 36 | 7 | 0.0 | 0.01 |
| 15 | 6 | 0.0 | 0.0 |
| 29 | 3 | 0.0 | 0.0 |

## q32_unknown_region_cause
```sql
-- Why is the region unknown? One row per cause, awards counted.
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT CASE WHEN b.ocid IS NULL THEN 'no buyer party found'
            WHEN b.postal IS NULL OR trim(b.postal) = '' THEN 'postal code missing'
            WHEN NOT regexp_matches(b.postal, '^[0-9]{5}$') THEN 'postal code not 5 digits'
            ELSE 'prefix not in cap_region' END AS cause,
       count(*) AS awards
FROM fact_award f LEFT JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' GROUP BY 1 ORDER BY 2 DESC;
```
| cause | awards |
|---|---|
| postal code not 5 digits | 24172 |
| no buyer party found | 59 |

## q33_unmapped_prefixes
```sql
-- For the last cause: the most frequent two-digit prefixes missing from the table.
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT left(b.postal, 2) AS prefix, count(*) AS awards
FROM fact_award f JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' AND regexp_matches(b.postal, '^[0-9]{5}$')
GROUP BY 1 ORDER BY 2 DESC LIMIT 15;
```
| prefix | awards |
|---|---|

## q34_unknown_region_by_year
```sql
SELECT award_year, count(*) AS awards,
       count(*) FILTER (WHERE region = 'unknown') AS unknown_region,
       round(100.0 * count(*) FILTER (WHERE region = 'unknown') / count(*), 1) AS pct_unknown
FROM fact_award GROUP BY 1 ORDER BY 1;
```
| award_year | awards | unknown_region | pct_unknown |
|---|---|---|---|
| 2000 | 1 | 0 | 0.0 |
| 2001 | 1 | 1 | 100.0 |
| 2002 | 2 | 0 | 0.0 |
| 2003 | 1 | 0 | 0.0 |
| 2008 | 3 | 0 | 0.0 |
| 2009 | 2 | 1 | 50.0 |
| 2010 | 5 | 0 | 0.0 |
| 2011 | 4 | 0 | 0.0 |
| 2012 | 2 | 0 | 0.0 |
| 2013 | 4 | 0 | 0.0 |
| 2014 | 8 | 0 | 0.0 |
| 2015 | 26 | 2 | 7.7 |
| 2016 | 60 | 2 | 3.3 |
| 2017 | 379 | 17 | 4.5 |
| 2018 | 58519 | 4175 | 7.1 |
| 2019 | 48353 | 3336 | 6.9 |
| 2020 | 55614 | 5869 | 10.6 |
| 2021 | 51322 | 3281 | 6.4 |
| 2022 | 85330 | 6096 | 7.1 |
| 2023 | 22426 | 1396 | 6.2 |
| 2024 | 664 | 29 | 4.4 |
| 2025 | 45 | 2 | 4.4 |
| 2027 | 2 | 0 | 0.0 |
| None | 203 | 24 | 11.8 |
