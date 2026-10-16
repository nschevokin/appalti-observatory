# Gate 1: validation at ingestion (ticket A4)
Run date: 2026-10-15T20:46:39+00:00
Input: `full.jsonl.gz`, sha256 `35266f3e1a5bfe5680207dd85ad18ad55858c9a2e8b7dc66447c94d5313ab720`

**Verdict: passed.** 5,165 of 562,886 processes rejected (0.9176%); the load aborts above 2%.

| Reason code | Rejected rows | Processes affected |
|---|---|---|
| missing_required | 24 | 24 |
| date_out_of_range | 0 | 0 |
| bad_amount | 0 | 0 |
| unexpected_currency | 0 | 0 |
| dangling_award_ref | 7 | 6 |
| dangling_party_ref | 5,135 | 5,135 |
| **all (distinct processes)** | 5,166 | 5,165 |

Flagged, not rejected (D014): 59,402 award dates outside the window.

Most frequent values behind each reason:

| Reason | Value | Rows |
|---|---|---|
| dangling_award_ref | `1444014` | 1 |
| dangling_award_ref | `1591543` | 1 |
| dangling_award_ref | `1637244` | 1 |
| dangling_party_ref | `buyer <11-digit id>` | 4,744 |
| dangling_party_ref | `buyer <16-character code>` | 355 |
| dangling_party_ref | `buyer <other id>` | 36 |
| missing_required | `missing: date, initiationType` | 24 |
