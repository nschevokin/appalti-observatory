"""D026: check the postal-code to region mapping on a hand-reviewed sample of buyers.

The sample sheet lists a postal code, a locality and the derived region; no name or identifier.
A reviewer writes `ok` or `wrong:<Region>` in the status column. Blank means not reviewed."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from appalti.stage import _connect

FIELDS = ["sample_id", "postal_code", "locality", "derived_region", "status"]


class RegionCheckError(Exception):
    """The review sheet is missing or incomplete."""


_PARTIES = '[{"roles":["VARCHAR"],"address":{"locality":"VARCHAR","postalCode":"VARCHAR"}}]'
_LOCALITY_SQL = (
    "SELECT trim(p.address.postalCode), min(p.address.locality) FROM ("
    f" SELECT unnest(from_json(doc->'$.parties', '{_PARTIES}')) AS p"
    " FROM raw WHERE hash(doc->>'$.ocid') % 16 = ?)"
    " WHERE list_contains(p.roles, 'buyer') AND p.address.locality IS NOT NULL"
    " GROUP BY 1"
)


def sample(db: Path, out: Path, n: int = 50, seed: int = 20261016) -> int:
    """Pick n buyer postal codes (legal-person buyers only), at most one per code."""
    con = _connect(db)
    try:
        rows = con.execute(
            "SELECT DISTINCT k.postal_code, c.region FROM party_key k"
            " JOIN cap_region c ON c.prefix = left(k.postal_code, 2)"
            " WHERE k.role = 'buyer' AND regexp_matches(k.key, '^IT-CF:[0-9]{11}$')"
            " AND regexp_matches(k.postal_code, '^[0-9]{5}$') ORDER BY k.postal_code"
        ).fetchall()
        picked = random.Random(seed).sample(rows, min(n, len(rows)))
        picked = sorted(picked)
        want = {postal for postal, _ in picked}
        found: dict[str, str] = {}
        for k in range(16):  # slices keep memory flat; stop once every code has a locality
            if want <= found.keys():
                break
            for postal, loc in con.execute(_LOCALITY_SQL, [k]).fetchall():
                if postal in want:
                    found.setdefault(postal, loc)
        out_rows = [
            {
                "sample_id": i,
                "postal_code": postal,
                "locality": found.get(postal, ""),
                "derived_region": region,
                "status": "",
            }
            for i, (postal, region) in enumerate(picked, start=1)
        ]
    finally:
        con.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    return len(out_rows)


def evaluate(path: Path, out: Path) -> dict:
    if not path.exists():
        raise RegionCheckError(f"{path} does not exist; run `appalti regions sample` first")
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    blank = [r["sample_id"] for r in rows if not r["status"].strip()]
    if blank:
        raise RegionCheckError(f"{len(blank)} of {len(rows)} rows are not reviewed yet")
    bad = [r for r in rows if r["status"].strip() != "ok" and not r["status"].startswith("wrong:")]
    if bad:
        raise RegionCheckError("status must be `ok` or `wrong:<Region>`")
    wrong = [r for r in rows if r["status"].startswith("wrong:")]
    res = {"n": len(rows), "wrong": len(wrong), "accuracy": 1 - len(wrong) / len(rows)}
    lines = [
        "# Region mapping check (D026)",
        "",
        f"{res['n']} buyer postal codes were reviewed by hand against their locality.",
        f"Wrong: {res['wrong']}. Accuracy: {100 * res['accuracy']:.1f}%.",
        "",
    ]
    if wrong:
        lines += ["| Postal code | Locality | Derived | Reviewer says |", "|---|---|---|---|"]
        lines += [
            f"| {r['postal_code']} | {r['locality']} | {r['derived_region']} | {r['status'][6:]} |"
            for r in wrong
        ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    return res
