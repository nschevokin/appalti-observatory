# Entities and award facts (tickets B1, B3)
Run `35266f3e-20261016T133519892111Z`, input `full.jsonl.gz`, sha256 `35266f3e1a5bfe5680207dd85ad18ad55858c9a2e8b7dc66447c94d5313ab720`.

Counts only; no identifier or name appears in this file (D009, D022, D030).

## Checks

| Check | Expected | Found | Status |
|---|---|---|---|
| fact_award rows equal clean awards | 322,976 | 322,976 | ok |
| fact_award has one row per (ocid, award_id) | 322,976 | 322,976 | ok |
| supplier shares sum to 1 on every award that has a supplier | 0 | 0 | ok |
| entity_id is unique | 97,249 | 97,249 | ok |
| every keyed party maps to an entity | 0 | 0 | ok |

## How parties were keyed

| Key method | Role | Party rows |
|---|---|---|
| identifier | buyer | 557,690 |
| identifier | supplier | 354,469 |
| identifier_padded | supplier | 46 |

## Entities

| Kind | Method | Entities |
|---|---|---|
| supplier | identifier | 77,887 |
| buyer | identifier | 18,536 |
| both | identifier | 826 |

Entities merged by an audited rule: 0 (the rule list is `apply_rules` in `audit.toml`).

## Award facts

- Award rows: 322,976 across 273,312 processes.
- Awards with a missing or unmapped buyer entity: 59.
- Awards with a published tenderer count: 0 (single_bidder is NULL on all others, D016).
- Awards dated outside the Gate 1 window (flagged, kept, D014): 59,222.

### Amount outliers (D025)

- Processes whose awards sum to more than 10 times the tender amount: 83 (221 awards, 87,809,512,408 EUR).
- Awarded value, all awards: 357,188,696,319 EUR.
- Awarded value, excluding flagged processes (headline): 269,379,183,912 EUR.

## Suppliers per award (D021)

| Linked suppliers | Awards |
|---|---|
| 0 | 867 |
| 1 | 292,050 |
| 2-5 | 27,478 |
| 6+ | 2,581 |

## Awards by buyer region (D026)

| Region | Awards |
|---|---|
| Lombardia | 56,425 |
| Lazio | 48,043 |
| Veneto | 24,822 |
| Piemonte | 24,271 |
| unknown | 24,231 |
| Emilia-Romagna | 22,870 |
| Toscana | 18,883 |
| Puglia | 12,844 |
| Trentino-Alto Adige | 11,433 |
| Sicilia | 11,142 |
| Campania | 10,788 |
| Friuli-Venezia Giulia | 10,135 |
| Sardegna | 8,892 |
| Marche | 8,180 |
| Liguria | 7,383 |
| Umbria | 6,573 |
| Abruzzo | 6,046 |
| Calabria | 3,764 |
| Basilicata | 2,948 |
| Valle d'Aosta | 2,085 |
| Molise | 1,218 |

