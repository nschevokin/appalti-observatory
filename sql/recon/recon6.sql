-- Sixth pass: the shape of the buyer postal codes that are not five digits (24,172 awards have
-- region 'unknown' for this reason). Shapes only: every digit is replaced by 9, every letter by A,
-- so no real code and no locality is printed. Reads the database built by `make entities`.

-- @query q35_postal_shapes
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

-- @query q36_four_digit_prefix_if_padded
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
