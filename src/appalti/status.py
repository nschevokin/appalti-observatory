"""`appalti status`: the current run, the counts and the last Gate 2 decisions."""

from __future__ import annotations

from pathlib import Path

import duckdb


def lines(db: Path) -> list[str]:
    if not db.exists():
        return [f"no database at {db}"]
    con = duckdb.connect(str(db), read_only=True)
    out: list[str] = []
    try:
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        if "run" in tables:
            for step in ("entities", "indicators", "gate2"):
                r = con.execute(
                    "SELECT run_id, started_at FROM run WHERE step = ?"
                    " ORDER BY started_at DESC, run_id DESC LIMIT 1",
                    [step],
                ).fetchone()
                out.append(f"{step:11} {r[0]}  {r[1]}" if r else f"{step:11} not run")
        for t in ("stg_release", "fact_award", "fact_award_supplier", "entity", "indicator_value"):
            if t in tables:
                out.append(f"{t:20} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>10,}")
        if "gate_decision" in tables:
            row = con.execute(
                "SELECT run_id, count(*), count(*) FILTER (WHERE NOT passed) FROM gate_decision"
                " GROUP BY 1 ORDER BY max(decision_id) DESC LIMIT 1"
            ).fetchone()
            if row:
                out.append(
                    f"gate_decision latest run {row[0]}: {row[1]} decisions, {row[2]} refused"
                )
    finally:
        con.close()
    return out
