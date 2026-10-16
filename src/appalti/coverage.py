"""Ticket A5: coverage table. Records per period and populatedness per field, computed on the
records that passed Gate 1, stored append-only and published as counts."""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from appalti import download as dl
from appalti.sqlblocks import split_blocks
from appalti.stage import _connect

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "coverage" / "030_coverage.sql"
FIRST_YEAR, LAST_YEAR = 2018, 2025
SECTIONS = [
    ("award_year", "award", "Awards by award year (the analysis clock, D015)"),
    ("tender_start_year", "process", "Processes by the year the tender started"),
    ("release_year", "process", "Processes by release year"),
]


class CoverageRefused(Exception):
    """Gate 1 has not produced clean records for the pinned file."""


@dataclass
class CoverageResult:
    run_id: str
    rows: int


def _band(gate_path: Path) -> tuple[float, float]:
    lo, hi = tomllib.loads(gate_path.read_text())["comparability"]["volume_ratio_band"]
    return float(lo), float(hi)


def run(file_name: str, manifest: Path, db: Path, gate_path: Path, out: Path) -> CoverageResult:
    entry = dl.load_manifest(manifest)["files"].get(file_name)
    if entry is None:
        raise CoverageRefused(f"{file_name} is not in {manifest}")
    now = dt.datetime.now(dt.UTC)
    run_id = f"{entry['sha256'][:8]}-{now:%Y%m%dT%H%M%S%fZ}"
    subs = {
        "$RUN_ID": run_id,
        "$MEASURED_AT": now.isoformat(timespec="seconds"),
        "$SHA": entry["sha256"],
    }
    text = SQL_FILE.read_text()
    for key, val in subs.items():
        text = text.replace(key, val)

    con = _connect(db)
    try:
        views = {r[0] for r in con.execute("SELECT view_name FROM duckdb_views()").fetchall()}
        if "clean_release" not in views:
            raise CoverageRefused("no clean_* views: run `appalti validate` and let Gate 1 pass")
        staged = con.execute("SELECT DISTINCT sha256 FROM stage_reconciliation").fetchall()
        if [r[0] for r in staged] != [entry["sha256"]]:
            raise CoverageRefused("staged tables were not built from the pinned file")
        for _, _, sql in split_blocks(text):
            con.execute(sql)
        rows = con.execute("SELECT count(*) FROM coverage WHERE run_id = ?", [run_id]).fetchone()[0]
        _write_report(con, run_id, entry, file_name, _band(gate_path), out)
    finally:
        con.close()
    return CoverageResult(run_id, int(rows))


def _pct(num: int, den: int) -> str:
    return "n/a" if den == 0 else f"{100 * num / den:.1f}%"


def _write_report(con, run_id: str, entry: dict, file_name: str, band, out: Path) -> None:
    lo, hi = band
    lines = [
        "# Coverage (ticket A5)",
        f"Run `{run_id}`, input `{file_name}`, sha256 `{entry['sha256']}`.",
        "",
        "Counted on the records that passed Gate 1. Each percentage is the share of that row's",
        "records in which the field is present; the denominator is the **Records** column.",
        f"`vs prev` is the record count divided by the previous year's; the accepted band is {lo}",
        f"to {hi} (`gate.toml`), and a year outside it is marked **outside**. This is a",
        "measurement, not a verdict: Gate 2 judges comparability per indicator.",
        "",
    ]
    for clock, unit, title in SECTIONS:
        data = con.execute(
            "SELECT period, field, n_total, n_populated FROM coverage"
            " WHERE run_id = ? AND clock = ? AND unit = ?",
            [run_id, clock, unit],
        ).fetchall()
        fields = sorted({f for _, f, _, _ in data if f != "records"})
        by_period: dict[str, dict[str, tuple[int, int]]] = {}
        for period, field, total, pop in data:
            by_period.setdefault(period, {})[field] = (total, pop)
        years = [str(y) for y in range(FIRST_YEAR, LAST_YEAR + 1)]
        other = {p: v for p, v in by_period.items() if p not in years}
        rows: list[tuple[str, dict[str, tuple[int, int]]]] = [
            (y, by_period[y]) for y in years if y in by_period
        ]
        if other:
            merged: dict[str, tuple[int, int]] = {}
            for v in other.values():
                for f, (t, p) in v.items():
                    a, b = merged.get(f, (0, 0))
                    merged[f] = (a + t, b + p)
            rows.append((f"outside {FIRST_YEAR}-{LAST_YEAR} or undated", merged))
        lines += [
            f"## {title}",
            "",
            "| Period | Records | vs prev | " + " | ".join(fields) + " |",
            "|---|---|---|" + "---|" * len(fields),
        ]
        prev: int | None = None
        for period, v in rows:
            n = v["records"][0]
            ratio = ""
            if period.isdigit() and prev:
                r = n / prev
                ratio = f"{r:.2f}" + (" **outside**" if not lo <= r <= hi else "")
            if period.isdigit():
                prev = n
            cells = [_pct(v[f][1], v[f][0]) if f in v else "n/a" for f in fields]
            lines.append(f"| {period} | {n:,} | {ratio} | " + " | ".join(cells) + " |")
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")


def history(db: Path) -> list[tuple[str, int]]:
    """Run ids kept in the coverage table, oldest first, with their row counts."""
    con = duckdb.connect(str(db), read_only=True)
    try:
        return [
            (r[0], int(r[1]))
            for r in con.execute(
                "SELECT run_id, count(*) FROM coverage GROUP BY run_id ORDER BY min(measured_at)"
            ).fetchall()
        ]
    finally:
        con.close()
