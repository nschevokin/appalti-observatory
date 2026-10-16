"""Tickets B1 and B3 as revised by D020 and D021: build the entity table from the normalised
identifier, then the award fact table and the supplier bridge. Counts only in the evidence file."""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from appalti import download as dl
from appalti.sqlblocks import split_blocks
from appalti.stage import _connect
from appalti.validate import load_gate

SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "entities"
SQL_FILES = ["040_entities.sql", "050_facts.sql"]


class EntitiesRefused(Exception):
    """Gate 1 has not produced clean records for the pinned file."""


@dataclass
class EntitiesResult:
    run_id: str
    checks: list[tuple[str, int, int]] = field(default_factory=list)  # name, expected, actual

    @property
    def failed(self) -> list[str]:
        return [n for n, want, got in self.checks if want != got]


def load_audit(path: Path) -> dict:
    return tomllib.loads(path.read_text())["audit"]


def _one(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0] or 0)


def run(
    file_name: str,
    manifest: Path,
    db: Path,
    gate_path: Path,
    audit_path: Path,
    cap_csv: Path,
    out: Path,
) -> EntitiesResult:
    entry = dl.load_manifest(manifest)["files"].get(file_name)
    if entry is None:
        raise EntitiesRefused(f"{file_name} is not in {manifest}")
    now = dt.datetime.now(dt.UTC)
    run_id = f"{entry['sha256'][:8]}-{now:%Y%m%dT%H%M%S%fZ}"
    gate = load_gate(gate_path)
    pub = dt.datetime.fromisoformat(entry["downloaded_at"]).date().isoformat()
    subs = {
        "$RUN_ID": run_id,
        "$MIN_DATE": gate["min_release_date"],
        "$PUB_DATE": pub,
        "$CAP_CSV": str(cap_csv),
    }
    audit = load_audit(audit_path)

    con = _connect(db)
    try:
        views = {r[0] for r in con.execute("SELECT view_name FROM duckdb_views()").fetchall()}
        if "clean_release" not in views:
            raise EntitiesRefused("no clean_* views: run `appalti validate` and let Gate 1 pass")
        staged = con.execute("SELECT DISTINCT sha256 FROM stage_reconciliation").fetchall()
        if [r[0] for r in staged] != [entry["sha256"]]:
            raise EntitiesRefused("staged tables were not built from the pinned file")

        con.execute("CREATE OR REPLACE TABLE entity_alias (key VARCHAR, merged_key VARCHAR)")
        if audit.get("apply_rules"):
            from appalti import audit as au  # local import: audit needs the tables built below

            con.close()
            au.build_alias_table(db, list(audit["apply_rules"]))
            con = _connect(db)
        con.execute(
            "CREATE TABLE IF NOT EXISTS run (run_id VARCHAR, step VARCHAR, started_at VARCHAR,"
            " sha256 VARCHAR, notes VARCHAR)"
        )
        con.execute(
            "INSERT INTO run VALUES (?, 'entities', ?, ?, ?)",
            [
                run_id,
                now.isoformat(timespec="seconds"),
                entry["sha256"],
                "apply_rules=" + ",".join(audit.get("apply_rules", [])),
            ],
        )
        for name in SQL_FILES:
            text = (SQL_DIR / name).read_text()
            for key, val in subs.items():
                text = text.replace(key, val)
            for kind, _, sql in split_blocks(text):
                if kind == "step":
                    con.execute(sql)
        result = EntitiesResult(run_id)
        _checks(con, result)
        _report(con, result, entry, file_name, out)
    finally:
        con.close()
    return result


def _checks(con: duckdb.DuckDBPyConnection, r: EntitiesResult) -> None:
    c = r.checks
    c.append(
        (
            "fact_award rows equal clean awards",
            _one(con, "SELECT count(*) FROM clean_award"),
            _one(con, "SELECT count(*) FROM fact_award"),
        )
    )
    c.append(
        (
            "fact_award has one row per (ocid, award_id)",
            _one(con, "SELECT count(*) FROM fact_award"),
            _one(con, "SELECT count(*) FROM (SELECT DISTINCT ocid, award_id FROM fact_award)"),
        )
    )
    c.append(
        (
            "supplier shares sum to 1 on every award that has a supplier",
            0,
            _one(
                con,
                "SELECT count(*) FROM (SELECT ocid, award_id, sum(share) AS s"
                " FROM fact_award_supplier GROUP BY 1, 2) WHERE abs(s - 1) > 1e-9",
            ),
        )
    )
    c.append(
        (
            "entity_id is unique",
            _one(con, "SELECT count(*) FROM entity"),
            _one(con, "SELECT count(DISTINCT entity_id) FROM entity"),
        )
    )
    c.append(
        (
            "every keyed party maps to an entity",
            0,
            _one(
                con,
                "SELECT count(*) FROM party_key k WHERE k.entity_key IS NOT NULL"
                " AND NOT EXISTS (SELECT 1 FROM entity e WHERE e.entity_key = k.entity_key)",
            ),
        )
    )


def _table(con, sql: str, headers: list[str]) -> list[str]:
    rows = con.execute(sql).fetchall()
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += [
        "| " + " | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in row) + " |"
        for row in rows
    ]
    return out + [""]


def _report(con, r: EntitiesResult, entry: dict, file_name: str, out: Path) -> None:
    total_value = con.execute("SELECT sum(amount_eur) FROM fact_award").fetchone()[0] or 0.0
    clean_value = (
        con.execute(
            "SELECT sum(amount_eur) FROM fact_award WHERE NOT inconsistent_amount"
        ).fetchone()[0]
        or 0.0
    )
    flagged = con.execute(
        "SELECT count(DISTINCT ocid), count(*), coalesce(sum(amount_eur), 0)"
        " FROM fact_award WHERE inconsistent_amount"
    ).fetchone()
    lines = [
        "# Entities and award facts (tickets B1, B3)",
        f"Run `{r.run_id}`, input `{file_name}`, sha256 `{entry['sha256']}`.",
        "",
        "Counts only; no identifier or name appears in this file (D009, D022, D030).",
        "",
        "## Checks",
        "",
        "| Check | Expected | Found | Status |",
        "|---|---|---|---|",
    ]
    lines += [f"| {n} | {w:,} | {g:,} | {'ok' if w == g else 'FAIL'} |" for n, w, g in r.checks]
    lines += ["", "## How parties were keyed", ""]
    lines += _table(
        con,
        "SELECT coalesce(key_method, 'no key') AS method, role, count(*) AS rows"
        " FROM party_key GROUP BY 1, 2 ORDER BY 2, 3 DESC",
        ["Key method", "Role", "Party rows"],
    )
    lines += ["## Entities", ""]
    lines += _table(
        con,
        "SELECT kind, method, count(*) FROM entity GROUP BY 1, 2 ORDER BY 3 DESC",
        ["Kind", "Method", "Entities"],
    )
    lines += [
        (
            "Entities merged by an audited rule: "
            f"{_one(con, "SELECT count(*) FROM entity WHERE method = 'name_match' AND identifier_id IS NOT NULL"):,}"
            " (the rule list is `apply_rules` in `audit.toml`)."
        ),
        "",
        "## Award facts",
        "",
        (
            f"- Award rows: {_one(con, 'SELECT count(*) FROM fact_award'):,}"
            f" across {_one(con, 'SELECT count(DISTINCT ocid) FROM fact_award'):,} processes."
        ),
        (
            f"- Awards with a missing or unmapped buyer entity: "
            f"{_one(con, 'SELECT count(*) FROM fact_award WHERE buyer_entity_id IS NULL'):,}."
        ),
        (
            f"- Awards with a published tenderer count: "
            f"{_one(con, 'SELECT count(*) FROM fact_award WHERE n_tenderers IS NOT NULL'):,}"
            " (single_bidder is NULL on all others, D016)."
        ),
        (
            f"- Awards dated outside the Gate 1 window (flagged, kept, D014): "
            f"{_one(con, 'SELECT count(*) FROM fact_award WHERE award_date_flagged'):,}."
        ),
        "",
        "### Amount outliers (D025)",
        "",
        (
            f"- Processes whose awards sum to more than 10 times the tender amount: {flagged[0]:,}"
            f" ({flagged[1]:,} awards, {flagged[2]:,.0f} EUR)."
        ),
        f"- Awarded value, all awards: {total_value:,.0f} EUR.",
        f"- Awarded value, excluding flagged processes (headline): {clean_value:,.0f} EUR.",
        "",
        "## Suppliers per award (D021)",
        "",
    ]
    lines += _table(
        con,
        "SELECT CASE WHEN n = 0 THEN '0' WHEN n = 1 THEN '1' WHEN n <= 5 THEN '2-5' ELSE '6+' END,"
        " count(*) FROM (SELECT a.ocid, a.award_id, coalesce(max(s.n), 0) AS n FROM fact_award a"
        " LEFT JOIN (SELECT ocid, award_id, count(*) AS n FROM fact_award_supplier GROUP BY 1, 2)"
        " s USING (ocid, award_id) GROUP BY 1, 2) GROUP BY 1 ORDER BY 1",
        ["Linked suppliers", "Awards"],
    )
    lines += ["## Awards by buyer region (D026)", ""]
    lines += _table(
        con,
        "SELECT region, count(*) FROM fact_award GROUP BY 1 ORDER BY 2 DESC",
        ["Region", "Awards"],
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
