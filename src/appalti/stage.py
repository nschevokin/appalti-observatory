"""Ticket A3: load a pinned raw OCDS file into typed staging tables and reconcile row counts.

The input must be pinned in manifest.json and match its sha256; otherwise nothing is loaded.
Every check lands in the `stage_reconciliation` table and in a markdown evidence file."""

from __future__ import annotations

import datetime as dt
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from appalti import download as dl
from appalti.sqlblocks import split_blocks

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "stage" / "010_stage.sql"


class NotPinned(Exception):
    """The raw file is not in the manifest, or differs from its pinned sha256."""


@dataclass
class Check:
    name: str
    expected: int | None
    actual: int
    note: str = ""

    @property
    def status(self) -> str:
        if self.expected is None:
            return "info"
        return "ok" if self.expected == self.actual else "MISMATCH"


def require_pinned(raw: Path, manifest_path: Path) -> str:
    entry = dl.load_manifest(manifest_path)["files"].get(raw.name)
    if entry is None:
        raise NotPinned(f"{raw.name} is not in {manifest_path}; run `appalti download` first")
    digest = dl.sha256_file(raw)
    if digest != entry["sha256"]:
        raise NotPinned(f"{raw.name}: {digest} differs from pinned {entry['sha256']}")
    return digest


def load_expected(path: Path, file_name: str) -> dict[str, int]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text()).get("files", {}).get(file_name, {})


def _one(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0] or 0)


CHUNKS = 64
_CREATE = re.compile(r"^CREATE OR REPLACE TABLE (\w+) AS", re.IGNORECASE | re.MULTILINE)


def run_chunked(con: duckdb.DuckDBPyConnection, sql: str, chunks: int = CHUNKS) -> None:
    """Run a CREATE TABLE AS step slice by slice: first slice creates, the rest INSERT."""
    m = _CREATE.search(sql)
    if m is None:
        raise ValueError("a chunked step must start with CREATE OR REPLACE TABLE <name> AS")
    for k in range(chunks):
        cond = f"hash(doc->>'$.ocid') % {chunks} = {k}"
        body = sql.replace("$CHUNK", cond)
        if k > 0:
            body = _CREATE.sub(f"INSERT INTO {m.group(1)}", body, count=1)
        con.execute(body)


def _connect(db: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db))
    con.execute("SET threads = 2")
    con.execute("SET preserve_insertion_order = false")
    Path("data/.duckdb_tmp").mkdir(parents=True, exist_ok=True)
    con.execute("SET temp_directory = 'data/.duckdb_tmp'")
    return con


def build(db: Path, raw: Path) -> None:
    """Run every step on its own connection, so memory is handed back between steps."""
    text = SQL_FILE.read_text().replace("$RAW_FILE", str(raw))
    for _, name, sql in split_blocks(text):
        con = _connect(db)
        try:
            if "$CHUNK" in sql:
                run_chunked(con, sql)
            else:
                con.execute(sql)
            con.execute("CHECKPOINT")
        finally:
            con.close()
        print(f"ok  {name}", flush=True)


def reconcile(con: duckdb.DuckDBPyConnection, expected: dict[str, int]) -> list[Check]:
    stated = {
        "lines": ("raw lines", "SELECT count(*) FROM raw"),
        "tenders": ("lines with a tender", "SELECT count(*) FROM stg_release WHERE has_tender"),
        "awards": ("awards", "SELECT count(*) FROM stg_award"),
        "contracts": ("contracts", "SELECT count(*) FROM stg_contract"),
        "parties": ("parties", "SELECT count(*) FROM stg_party"),
        "supplier_role_rows": (
            "party rows with role supplier",
            "SELECT count(*) FROM stg_party WHERE role = 'supplier'",
        ),
        "award_supplier_refs": (
            "award-supplier references",
            "SELECT count(*) FROM stg_award_supplier",
        ),
        "milestones": (
            "milestones (tender + contract level)",
            (
                "SELECT coalesce(sum(n_milestones_tender), 0) FROM stg_release"
                " UNION ALL SELECT coalesce(sum(n_milestones), 0) FROM stg_contract"
            ),
        ),
    }
    checks: list[Check] = []
    for key, (label, sql) in stated.items():
        if key == "milestones":
            tender_ms, contract_ms = (r[0] for r in con.execute(sql).fetchall())
            checks.append(
                Check(
                    label,
                    expected.get(key),
                    int(tender_ms + contract_ms),
                    f"tender level {int(tender_ms)}, contract level {int(contract_ms)}",
                )
            )
        else:
            checks.append(Check(label, expected.get(key), _one(con, sql)))

    internal = [
        (
            "distinct ocid equals lines",
            _one(con, "SELECT count(*) FROM raw"),
            _one(con, "SELECT count(DISTINCT ocid) FROM stg_release"),
        ),
        (
            "stg_release rows equal raw lines",
            _one(con, "SELECT count(*) FROM raw"),
            _one(con, "SELECT count(*) FROM stg_release"),
        ),
        (
            "stg_party rows equal sum of parties arrays",
            _one(con, "SELECT sum(n_parties) FROM stg_release"),
            _one(con, "SELECT count(*) FROM stg_party"),
        ),
        (
            "stg_award rows equal sum of awards arrays",
            _one(con, "SELECT sum(n_awards) FROM stg_release"),
            _one(con, "SELECT count(*) FROM stg_award"),
        ),
        (
            "stg_contract rows equal sum of contracts arrays",
            _one(con, "SELECT sum(n_contracts) FROM stg_release"),
            _one(con, "SELECT count(*) FROM stg_contract"),
        ),
        (
            "stg_award_supplier rows equal sum of suppliers arrays",
            _one(con, "SELECT sum(n_suppliers) FROM stg_award"),
            _one(con, "SELECT count(*) FROM stg_award_supplier"),
        ),
    ]
    checks += [Check(name, exp, act, "internal") for name, exp, act in internal]
    checks += [
        Check(
            "award amounts present but not numeric (left NULL, for Gate 1)",
            None,
            _one(
                con,
                "SELECT count(*) FROM stg_award WHERE amount_raw IS NOT NULL AND amount IS NULL",
            ),
        ),
        Check(
            "award dates present but unreadable (year NULL, for Gate 1)",
            None,
            _one(
                con,
                "SELECT count(*) FROM stg_award"
                " WHERE award_date_raw IS NOT NULL AND award_year IS NULL",
            ),
        ),
    ]
    return checks


def write_outputs(
    con: duckdb.DuckDBPyConnection, checks: list[Check], raw: Path, sha: str, out: Path
) -> None:
    now = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    con.execute(
        "CREATE OR REPLACE TABLE stage_reconciliation (check_name VARCHAR, expected BIGINT,"
        " actual BIGINT, status VARCHAR, note VARCHAR, run_at VARCHAR, sha256 VARCHAR)"
    )
    for c in checks:
        con.execute(
            "INSERT INTO stage_reconciliation VALUES (?, ?, ?, ?, ?, ?, ?)",
            [c.name, c.expected, c.actual, c.status, c.note, now, sha],
        )
    lines = [
        "# Staging reconciliation (ticket A3)",
        f"Run date: {now}",
        f"Input: `{raw.name}`, sha256 `{sha}`",
        "",
        "| Check | Stated | Staged | Status | Note |",
        "|---|---|---|---|---|",
    ]
    for c in checks:
        exp = "" if c.expected is None else f"{c.expected:,}"
        lines.append(f"| {c.name} | {exp} | {c.actual:,} | {c.status} | {c.note} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def run(raw: Path, manifest: Path, db: Path, expected_path: Path, out: Path) -> list[Check]:
    sha = require_pinned(raw, manifest)
    db.parent.mkdir(parents=True, exist_ok=True)
    build(db, raw)
    con = _connect(db)
    try:
        checks = reconcile(con, load_expected(expected_path, raw.name))
        write_outputs(con, checks, raw, sha, out)
    finally:
        con.close()
    return checks
