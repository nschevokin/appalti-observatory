"""Ticket C1: compute the four indicators on both clocks and write evidence/indicators.md.

Nothing here judges comparability; that is Gate 2 (gate2.py). Named entities never appear:
concentration is a share, not a list."""

from __future__ import annotations

import datetime as dt
import tomllib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from appalti import download as dl
from appalti.audit import LEGAL_TOKENS
from appalti.sqlblocks import split_blocks
from appalti.stage import _connect

SQL_FILE = Path(__file__).resolve().parents[2] / "sql" / "indicators" / "060_indicators.sql"
CLOCKS = ["award_year", "tender_year"]
LEGAL_RE = "(^|[^A-Z0-9])(" + "|".join(sorted(LEGAL_TOKENS)) + ")([^A-Z0-9]|$)"
INDICATORS = ["awarded_value", "single_bidder", "concentration", "procedure_mix"]


class IndicatorsRefused(Exception):
    """The fact tables are missing or were not built from the pinned file."""


@dataclass
class IndicatorResult:
    run_id: str
    rows: int
    outside: dict[str, int]


def load_window(gate_path: Path) -> tuple[int, int]:
    w = tomllib.loads(gate_path.read_text())["window"]
    return int(w["first_period"]), int(w["last_period"])


def latest_run(con: duckdb.DuckDBPyConnection, step: str) -> tuple[str, str] | None:
    row = con.execute(
        "SELECT run_id, sha256 FROM run WHERE step = ? ORDER BY started_at DESC, run_id DESC LIMIT 1",
        [step],
    ).fetchone()
    return (row[0], row[1]) if row else None


def run(
    file_name: str, manifest: Path, db: Path, gate_path: Path, proc_csv: Path, out: Path
) -> IndicatorResult:
    entry = dl.load_manifest(manifest)["files"].get(file_name)
    if entry is None:
        raise IndicatorsRefused(f"{file_name} is not in {manifest}")
    first, last = load_window(gate_path)
    now = dt.datetime.now(dt.UTC)
    run_id = f"{entry['sha256'][:8]}-{now:%Y%m%dT%H%M%S%fZ}"
    con = _connect(db)
    try:
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        if not {"fact_award", "fact_award_supplier", "entity", "run"} <= tables:
            raise IndicatorsRefused("no fact tables: run `appalti resolve build` first")
        ent = latest_run(con, "entities")
        if ent is None or ent[1] != entry["sha256"]:
            raise IndicatorsRefused("the fact tables were not built from the pinned file")
        con.execute(
            "INSERT INTO run VALUES (?, 'indicators', ?, ?, ?)",
            [run_id, now.isoformat(timespec="seconds"), entry["sha256"], f"entities={ent[0]}"],
        )
        subs = {
            "$PROC_CSV": str(proc_csv),
            "$RUN_ID": run_id,
            "$FIRST": str(first),
            "$LAST": str(last),
            "$LEGAL_RE": LEGAL_RE,
        }
        text = SQL_FILE.read_text()
        for key, val in subs.items():
            text = text.replace(key, val)
        for kind, _, sql in split_blocks(text):
            if kind == "step":
                con.execute(sql)
        rows = int(con.execute("SELECT count(*) FROM indicator_value").fetchone()[0])
        outside = {
            "award_year": int(
                con.execute(
                    "SELECT count(*) FROM fact_award WHERE award_year IS NULL"
                    " OR award_year NOT BETWEEN ? AND ?",
                    [first, last],
                ).fetchone()[0]
            ),
            "tender_year": int(
                con.execute(
                    "SELECT count(*) FROM fact_award WHERE tender_year IS NULL"
                    " OR tender_year NOT BETWEEN ? AND ?",
                    [first, last],
                ).fetchone()[0]
            ),
        }
        _report(con, run_id, entry, file_name, (first, last), outside, out)
    finally:
        con.close()
    return IndicatorResult(run_id, rows, outside)


def _bn(x: float | None) -> str:
    return "n/a" if x is None else f"{x / 1e9:,.2f}"


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _report(con, run_id, entry, file_name, window, outside, out: Path) -> None:
    first, last = window
    total = int(con.execute("SELECT count(*) FROM fact_award").fetchone()[0])
    lines = [
        "# Indicators (ticket C1)",
        f"Run `{run_id}`, input `{file_name}`, sha256 `{entry['sha256']}`.",
        "",
        "Every row carries its **n** (awards behind the figure) and, where a field can be absent,",
        "its populatedness. These are measurements: whether two years may be compared is decided",
        "by Gate 2 (`evidence/gate2.md`). Figures are awarded (not spent) euro; threshold 40,000",
        "euro, so below-threshold contracts are absent. No entity is named anywhere.",
        "",
        (
            f"Window {first} to {last}. Awards outside it, or without a year, are not in any figure: "
            f"{outside['award_year']:,} of {total:,} on the award-year clock, "
            f"{outside['tender_year']:,} on the tender-start-year clock."
        ),
        "",
    ]
    pop = {
        (r[0], r[1], r[2]): (r[3], r[4])
        for r in con.execute(
            "SELECT indicator, clock, period, n, n_populated FROM ind_populatedness"
        ).fetchall()
    }

    def popstr(ind, clock, period):
        n, p = pop.get((ind, clock, period), (0, 0))
        return f"{n:,}", _pct(p / n if n else None)

    for clock in CLOCKS:
        lines += [f"## Awarded value, {clock.replace('_', ' ')} clock (billion EUR)", ""]
        lines += [
            "| Period | Awards | Populated | Headline | All awards | Flagged (D025) | Flagged awards |",
            "|---|---|---|---|---|---|---|",
        ]
        rows = con.execute(
            "SELECT period,"
            " max(value) FILTER (WHERE variant = 'headline'),"
            " max(value) FILTER (WHERE variant = 'all'),"
            " max(value) FILTER (WHERE variant = 'flagged'),"
            " max(n) FILTER (WHERE variant = 'flagged')"
            " FROM indicator_value WHERE indicator = 'awarded_value' AND slice_type = 'all'"
            " AND clock = ? GROUP BY 1 ORDER BY 1",
            [clock],
        ).fetchall()
        for period, h, a, fl, fn in rows:
            n, p = popstr("awarded_value", clock, period)
            lines.append(f"| {period} | {n} | {p} | {_bn(h)} | {_bn(a)} | {_bn(fl)} | {fn:,} |")
        lines.append("")
    for clock in CLOCKS:
        lines += [f"## Supplier concentration (top five), {clock.replace('_', ' ')} clock", ""]
        lines += [
            "Share of the year's headline awarded value that went to the five largest suppliers.",
            "`Point` treats every identifier as one entity; `upper` also merges ids that share a",
            "legal-form name, so the truth lies between them (D036: split rate about 7%, wide interval).",
            "",
            "| Period | Awards used | Populated | Point | Upper |",
            "|---|---|---|---|---|",
        ]
        rows = con.execute(
            "SELECT period, max(n), max(value) FILTER (WHERE variant = 'point'),"
            " max(value) FILTER (WHERE variant = 'merged_upper')"
            " FROM indicator_value WHERE indicator = 'concentration' AND clock = ?"
            " GROUP BY 1 ORDER BY 1",
            [clock],
        ).fetchall()
        for period, n, pt, up in rows:
            _, p = popstr("concentration", clock, period)
            lines.append(f"| {period} | {n:,} | {p} | {_pct(pt)} | {_pct(up)} |")
        lines.append("")
    classes = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT variant FROM indicator_value WHERE indicator = 'procedure_mix'"
            " ORDER BY 1"
        ).fetchall()
    ]
    for clock in CLOCKS:
        lines += [f"## Procedure mix, share of awarded value, {clock.replace('_', ' ')} clock", ""]
        lines += [
            "| Period | Populated | " + " | ".join(classes) + " |",
            "|---|---|" + "---|" * len(classes),
        ]
        periods = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT period FROM indicator_value WHERE indicator = 'procedure_mix'"
                " AND clock = ? ORDER BY 1",
                [clock],
            ).fetchall()
        ]
        for period in periods:
            vals = dict(
                con.execute(
                    "SELECT variant, value FROM indicator_value WHERE indicator = 'procedure_mix'"
                    " AND clock = ? AND period = ?",
                    [clock, period],
                ).fetchall()
            )
            _, p = popstr("procedure_mix", clock, period)
            lines.append(
                f"| {period} | {p} | " + " | ".join(_pct(vals.get(c)) for c in classes) + " |"
            )
        lines.append("")
    lines += ["## Single-bidder share", ""]
    lines += [
        "| Clock | Period | Awards with a tenderer count | Of all awards | Value |",
        "|---|---|---|---|---|",
    ]
    for clock, period, n, v in con.execute(
        "SELECT clock, period, n, value FROM indicator_value WHERE indicator = 'single_bidder'"
        " ORDER BY 1, 2"
    ).fetchall():
        _, p = popstr("single_bidder", clock, period)
        lines.append(f"| {clock} | {period} | {n:,} | {p} | {_pct(v)} |")
    lines += [
        "",
        "A value of n/a means the field is empty and the share cannot be computed (D016).",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
