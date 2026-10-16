# Recon output
Run date: 2026-10-16T14:30:24+00:00
Input: `data/raw/full.jsonl.gz`
DuckDB: 1.5.6

## q35_postal_shapes
```sql
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT regexp_replace(regexp_replace(b.postal, '[0-9]', '9', 'g'), '[A-Za-z]', 'A', 'g') AS shape,
       length(b.postal) AS len, count(*) AS awards
FROM fact_award f JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' AND b.postal IS NOT NULL AND NOT regexp_matches(b.postal, '^[0-9]{5}$')
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 20;
```
| shape | len | awards |
|---|---|---|
| A.A. | 4 | 23259 |
| 999 | 3 | 913 |

## q36_four_digit_prefix_if_padded
```sql
-- If the 4-digit codes lost a leading zero, padding gives these two-digit prefixes.
WITH b AS (
  SELECT t.ocid, any_value(k.postal_code) AS postal
  FROM tmp_release_check t
  JOIN party_key k ON k.ocid = t.ocid AND k.pid = t.buyer_id AND k.role = 'buyer'
  GROUP BY 1)
SELECT left('0' || b.postal, 2) AS prefix_if_padded, count(*) AS awards
FROM fact_award f JOIN b ON b.ocid = f.ocid
WHERE f.region = 'unknown' AND regexp_matches(b.postal, '^[0-9]{4}$')
GROUP BY 1 ORDER BY 2 DESC;
```
| prefix_if_padded | awards |
|---|---|
