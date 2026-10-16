"""Ticket A4: Gate 1. Check every staged record, write failures to rejected_record with a reason
code, publish the reject counts, and abort when too many processes fail."""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from appalti import download as dl
from appalti.sqlblocks import split_blocks
from appalti.stage import _connect, load_expected

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "validate" / "020_validate.sql"
REASONS = [
    "missing_required",
    "date_out_of_range",
    "bad_amount",
    "unexpected_currency",
    "dangling_award_ref",
    "dangling_party_ref",
]
CLEAN_VIEWS = [
    "rejected_ocid",
    "clean_release",
    "clean_party",
    "clean_award",
    "clean_award_supplier",
    "clean_contract",
]


class StageMismatch(Exception):
    """The staged tables were not built from the pinned file."""


@dataclass
class Gate1Result:
    lines: int
    rejected_rows: int
    rejected_processes: int
    max_share: float
    by_reason: list[tuple[str, int, int]]
    flagged_award_dates: int
    expectation_mismatches: list[str] = field(default_factory=list)
    samples: list[tuple[str, str, int]] = field(default_factory=list)

    @property
    def share(self) -> float:
        return self.rejected_processes / self.lines if self.lines else 0.0

    @property
    def aborted(self) -> bool:
        return self.share > self.max_share


def load_gate(path: Path) -> dict:
    return tomllib.loads(path.read_text())["gate1"]


def _publication_date(entry: dict) -> str:
    return dt.datetime.fromisoformat(entry["downloaded_at"]).date().isoformat()


def _one(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0] or 0)


def run(
    file_name: str,
    manifest: Path,
    db: Path,
    gate_path: Path,
    expected_path: Path,
    out: Path,
) -> Gate1Result:
    entry = dl.load_manifest(manifest)["files"].get(file_name)
    if entry is None:
        raise StageMismatch(f"{file_name} is not in {manifest}")
    gate = load_gate(gate_path)
    subs = {
        "$MIN_DATE": gate["min_release_date"],
        "$PUB_DATE": _publication_date(entry),
        "$CURRENCIES": ", ".join("'" + c + "'" for c in gate["allowed_currencies"]),
    }
    text = SQL_FILE.read_text()
    for key, val in subs.items():
        text = text.replace(key, val)

    con = _connect(db)
    try:
        staged = con.execute("SELECT DISTINCT sha256 FROM stage_reconciliation").fetchall()
        if [r[0] for r in staged] != [entry["sha256"]]:
            raise StageMismatch("staged tables were not built from the pinned file; run stage")
        for kind, _, sql in split_blocks(text):
            if kind == "step":
                con.execute(sql)
        lines = _one(con, "SELECT count(*) FROM raw")
        result = Gate1Result(
            lines=lines,
            rejected_rows=_one(con, "SELECT count(*) FROM rejected_record"),
            rejected_processes=_one(
                con, "SELECT count(DISTINCT coalesce(ocid, '<no ocid>')) FROM rejected_record"
            ),
            max_share=float(gate["max_reject_share"]),
            by_reason=[
                (
                    reason,
                    _one(con, f"SELECT count(*) FROM rejected_record WHERE reason = '{reason}'"),
                    _one(
                        con,
                        "SELECT count(DISTINCT coalesce(ocid, '<no ocid>')) FROM rejected_record"
                        f" WHERE reason = '{reason}'",
                    ),
                )
                for reason in REASONS
            ],
            flagged_award_dates=_one(con, "SELECT count(*) FROM flagged_record"),
        )
        # Identifiers are never printed: the report is public and a 16-character code is a
        # natural person's fiscal code (D009, D022). Party-reference values are reduced to a class.
        result.samples = [
            (r[0], r[1] or "", int(r[2]))
            for r in con.execute(
                "WITH m AS (SELECT reason, CASE WHEN reason = 'dangling_party_ref' THEN"
                " split_part(detail, ' ', 1) || ' <' || CASE"
                " WHEN regexp_matches(split_part(detail, ' ', 2), '^[0-9]{11}$') THEN '11-digit id'"
                " WHEN length(split_part(detail, ' ', 2)) = 16 THEN '16-character code'"
                " WHEN split_part(detail, ' ', 2) = '<null>' THEN 'null id'"
                " ELSE 'other id' END || '>' ELSE detail END AS detail FROM rejected_record)"
                " SELECT reason, detail, n FROM ("
                " SELECT reason, detail, count(*) AS n,"
                "  row_number() OVER (PARTITION BY reason ORDER BY count(*) DESC, detail) AS rk"
                " FROM m GROUP BY reason, detail) WHERE rk <= 3"
                " ORDER BY reason, n DESC"
            ).fetchall()
        ]
        # an aborted load must leave no clean_* views behind for later steps to use
        for view in CLEAN_VIEWS:
            con.execute(f"DROP VIEW IF EXISTS {view}")
        if not result.aborted:
            for kind, _, sql in split_blocks(text):
                if kind == "clean":
                    con.execute(sql)
        _compare_expected(result, load_expected(expected_path, file_name))
        _store_summary(con, result)
    finally:
        con.close()
    _write_report(result, entry, file_name, out)
    return result


def _compare_expected(result: Gate1Result, expected: dict[str, int]) -> None:
    rows = {name: n for name, n, _ in result.by_reason}
    actual = {f"gate1_{name}": n for name, n in rows.items()}
    actual["gate1_flagged_award_date"] = result.flagged_award_dates
    for key, want in expected.items():
        if key.startswith("gate1_") and actual.get(key) != want:
            result.expectation_mismatches.append(f"{key}: stated {want:,}, found {actual.get(key)}")


def _store_summary(con: duckdb.DuckDBPyConnection, r: Gate1Result) -> None:
    con.execute(
        "CREATE OR REPLACE TABLE gate1_summary (reason VARCHAR, rows BIGINT, processes BIGINT)"
    )
    for reason, n, procs in r.by_reason:
        con.execute("INSERT INTO gate1_summary VALUES (?, ?, ?)", [reason, n, procs])
    con.execute(
        "INSERT INTO gate1_summary VALUES ('ALL', ?, ?)", [r.rejected_rows, r.rejected_processes]
    )


def _write_report(r: Gate1Result, entry: dict, file_name: str, out: Path) -> None:
    now = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    verdict = "ABORTED" if r.aborted else "passed"
    lines = [
        "# Gate 1: validation at ingestion (ticket A4)",
        f"Run date: {now}",
        f"Input: `{file_name}`, sha256 `{entry['sha256']}`",
        "",
        (
            f"**Verdict: {verdict}.** {r.rejected_processes:,} of {r.lines:,} processes rejected "
            f"({r.share:.4%}); the load aborts above {r.max_share:.0%}."
        ),
        "",
        "| Reason code | Rejected rows | Processes affected |",
        "|---|---|---|",
    ]
    lines += [f"| {name} | {n:,} | {p:,} |" for name, n, p in r.by_reason]
    lines += [
        f"| **all (distinct processes)** | {r.rejected_rows:,} | {r.rejected_processes:,} |",
        "",
        f"Flagged, not rejected (D014): {r.flagged_award_dates:,} award dates outside the window.",
    ]
    if r.samples:
        lines += [
            "",
            "Most frequent values behind each reason:",
            "",
            "| Reason | Value | Rows |",
            "|---|---|---|",
        ]
        lines += [f"| {a} | `{b}` | {n:,} |" for a, b, n in r.samples]
    if r.expectation_mismatches:
        lines += ["", "Differences from the numbers stated in the recon:"]
        lines += [f"- {m}" for m in r.expectation_mismatches]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
