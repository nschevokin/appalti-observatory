# Staging reconciliation (ticket A3)
Run date: 2026-10-15T20:05:55+00:00
Input: `full.jsonl.gz`, sha256 `35266f3e1a5bfe5680207dd85ad18ad55858c9a2e8b7dc66447c94d5313ab720`

| Check | Stated | Staged | Status | Note |
|---|---|---|---|---|
| raw lines | 562,886 | 562,886 | ok |  |
| lines with a tender | 562,862 | 562,862 | ok |  |
| awards | 324,030 | 324,030 | ok |  |
| contracts | 185,259 | 185,259 | ok |  |
| parties | 1,474,656 | 1,474,656 | ok |  |
| party rows with role supplier | 355,681 | 355,681 | ok |  |
| award-supplier references | 390,526 | 390,526 | ok |  |
| milestones (tender + contract level) | 83,587 | 83,587 | ok | tender level 0, contract level 83587 |
| distinct ocid equals lines | 562,886 | 562,886 | ok | internal |
| stg_release rows equal raw lines | 562,886 | 562,886 | ok | internal |
| stg_party rows equal sum of parties arrays | 1,474,656 | 1,474,656 | ok | internal |
| stg_award rows equal sum of awards arrays | 324,030 | 324,030 | ok | internal |
| stg_contract rows equal sum of contracts arrays | 185,259 | 185,259 | ok | internal |
| stg_award_supplier rows equal sum of suppliers arrays | 390,526 | 390,526 | ok | internal |
| award amounts present but not numeric (left NULL, for Gate 1) |  | 0 | info |  |
| award dates present but unreadable (year NULL, for Gate 1) |  | 0 | info |  |
