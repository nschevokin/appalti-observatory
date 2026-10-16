"""Ticket C2: Gate 2, comparability before publication.

For every indicator and clock it judges each period (is the field populated enough?) and each
pair of consecutive periods (populatedness spread, volume ratio, composition drift) against the
thresholds fixed in gate.toml, and records every judgement in `gate_decision`. A refusal carries
its reason as text; the site prints that text where the comparison would have been."""

from __future__ import annotations

import datetime as dt
import itertools
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from appalti.indicators import CLOCKS, INDICATORS, IndicatorsRefused, latest_run
from appalti.stage import _connect

LABELS = {
    "awarded_value": "Awarded value",
    "single_bidder": "Single-bidder share",
    "concentration": "Supplier concentration",
    "procedure_mix": "Procedure mix",
}
REQUIRED = {
    "awarded_value": "award amount",
    "concentration": "award amount and a linked supplier",
    "procedure_mix": "procedure code",
}
CLOCK_NAMES = {"award_year": "award year", "tender_year": "tender start year"}


@dataclass
class Gate2Result:
    run_id: str
    decisions: int
    refusals: int
    passed: int


def load_thresholds(path: Path) -> dict:
    cfg = tomllib.loads(path.read_text())
    return cfg


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _drift(a: dict[str, int], b: dict[str, int]) -> float:
    ta, tb = sum(a.values()) or 1, sum(b.values()) or 1
    keys = set(a) | set(b)
    return 0.5 * sum(abs(a.get(k, 0) / ta - b.get(k, 0) / tb) for k in keys)


def _field(cfg: dict, indicator: str) -> str:
    req = cfg.get("indicators", {}).get(indicator, {}).get("requires")
    return ", ".join(req) if req else REQUIRED[indicator]


def judge_period(cfg, indicator, period, n, n_pop) -> tuple[dict, list[dict]]:
    th = cfg["comparability"]
    pop = n_pop / n if n else 0.0
    measures = {"n": n, "n_populated": n_pop, "populatedness": pop}
    failed = []
    if pop < th["min_populatedness"]:
        failed.append(
            {
                "measure": "populatedness",
                "value": pop,
                "text": (
                    f"The required field ({_field(cfg, indicator)}) is populated in "
                    f"{_pct(pop)} of {period} records, below the minimum of "
                    f"{_pct(th['min_populatedness'])}."
                ),
            }
        )
    return measures, failed


def judge_pair(cfg, indicator, a, b, na, pa, nb, pb, comp_a, comp_b) -> tuple[dict, list[dict]]:
    th = cfg["comparability"]
    lo, hi = th["volume_ratio_band"]
    ratio = nb / na if na else float("inf")
    spread = abs(pb - pa)
    drift = _drift(comp_a, comp_b)
    measures = {
        "n_a": na, "n_b": nb, "populatedness_a": pa, "populatedness_b": pb,
        "populatedness_spread": spread, "volume_ratio": ratio, "composition_drift": drift,
    }  # fmt: skip
    failed = []
    low = [(period, p) for period, p in ((a, pa), (b, pb)) if p < th["min_populatedness"]]
    if low:
        what = " and ".join(f"{_pct(p)} of {period} records" for period, p in low)
        failed.append(
            {
                "measure": "populatedness",
                "value": min(p for _, p in low),
                "text": (
                    f"The required field ({_field(cfg, indicator)}) is populated in {what}, "
                    f"below the minimum of {_pct(th['min_populatedness'])}."
                ),
            }
        )
    if spread > th["max_populatedness_spread"]:
        failed.append(
            {
                "measure": "populatedness_spread",
                "value": spread,
                "text": (
                    f"Populatedness differs by {100 * spread:.1f} points between the two years, "
                    f"above the maximum of {100 * th['max_populatedness_spread']:.0f}."
                ),
            }
        )
    if not lo <= ratio <= hi:
        failed.append(
            {
                "measure": "volume_ratio",
                "value": ratio,
                "text": (
                    f"The {b} record count is {ratio:.2f} of the {a} count, outside the accepted "
                    f"band of {lo} to {hi}."
                ),
            }
        )
    if drift > th["max_composition_drift"]:
        failed.append(
            {
                "measure": "composition_drift",
                "value": drift,
                "text": (
                    f"The sector mix (CPV division) shifted by {drift:.3f}, above the accepted "
                    f"maximum of {th['max_composition_drift']}."
                ),
            }
        )
    return measures, failed


def refusal_text(indicator: str, clock: str, periods: list[str], reasons: dict) -> str:
    what = f"{LABELS[indicator]}, "
    what += f"{periods[0]}" if len(periods) == 1 else f"{periods[0]} compared with {periods[1]}"
    body = " ".join(f["text"] for f in reasons["failed"])
    if any(f["measure"] == "isolated" for f in reasons["failed"]):
        tail = "A year with no comparable neighbour is not published (D040)."
    elif len(periods) == 2:
        tail = "The two years are not comparable on this measure."
    else:
        tail = "The figure cannot be computed honestly for this year."
    return f"{what} ({CLOCK_NAMES[clock]}): not published. {body} {tail}"


def check(db: Path, gate_path: Path, out: Path) -> Gate2Result:
    cfg = load_thresholds(gate_path)
    first, last = int(cfg["window"]["first_period"]), int(cfg["window"]["last_period"])
    now = dt.datetime.now(dt.UTC)
    con = _connect(db)
    try:
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        if not {"ind_populatedness", "ind_composition", "indicator_value"} <= tables:
            raise IndicatorsRefused("no indicator tables: run `appalti indicators` first")
        ind = latest_run(con, "indicators")
        if ind is None:
            raise IndicatorsRefused("no indicators run recorded")
        run_id = f"{ind[1][:8]}-G{now:%Y%m%dT%H%M%S%fZ}"
        con.execute(
            "CREATE TABLE IF NOT EXISTS gate_decision (decision_id BIGINT, ran_at TIMESTAMP,"
            " indicator VARCHAR, clock VARCHAR, periods VARCHAR[], passed BOOLEAN, reasons JSON,"
            " thresholds JSON, run_id VARCHAR)"
        )
        con.execute(
            "INSERT INTO run VALUES (?, 'gate2', ?, ?, ?)",
            [run_id, now.isoformat(timespec="seconds"), ind[1], f"indicators={ind[0]}"],
        )
        next_id = int(
            con.execute("SELECT coalesce(max(decision_id), 0) FROM gate_decision").fetchone()[0]
        )
        thresholds = json.dumps({**cfg["comparability"], "window": [first, last]})
        pop = {
            (r[0], r[1], r[2]): (r[3], r[4])
            for r in con.execute(
                "SELECT indicator, clock, period, n, n_populated FROM ind_populatedness"
                " WHERE period BETWEEN ? AND ?",
                [first, last],
            ).fetchall()
        }
        comp: dict[tuple[str, int], dict[str, int]] = {}
        for clock, period, cpv, n in con.execute(
            "SELECT clock, period, cpv_division, n FROM ind_composition"
        ).fetchall():
            comp.setdefault((clock, period), {})[cpv] = n
        rows = []
        for indicator in INDICATORS:
            for clock in CLOCKS:
                periods = sorted(p for (i, c, p) in pop if i == indicator and c == clock)
                for p in periods:
                    n, npop = pop[(indicator, clock, p)]
                    m, failed = judge_period(cfg, indicator, p, n, npop)
                    rows.append((indicator, clock, [str(p)], m, failed))
                for a, b in itertools.pairwise(periods):
                    if b != a + 1:
                        continue
                    (na, npa), (nb, npb) = pop[(indicator, clock, a)], pop[(indicator, clock, b)]
                    m, failed = judge_pair(
                        cfg, indicator, a, b, na, npa / na if na else 0.0,
                        nb, npb / nb if nb else 0.0,
                        comp.get((clock, a), {}), comp.get((clock, b), {}),
                    )  # fmt: skip
                    rows.append((indicator, clock, [str(a), str(b)], m, failed))
        rows = _isolate(rows)
        for indicator, clock, per, measures, failed in rows:
            next_id += 1
            con.execute(
                "INSERT INTO gate_decision VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    next_id, now.replace(tzinfo=None), indicator, clock, per, not failed,
                    json.dumps({"measures": measures, "failed": failed}), thresholds, run_id,
                ],
            )  # fmt: skip
        refusals = sum(1 for r in rows if r[4])
        res = Gate2Result(run_id, len(rows), refusals, len(rows) - refusals)
        _report(con, cfg, run_id, ind[0], res, out)
    finally:
        con.close()
    return res


def _isolate(rows: list) -> list:
    """D040 (post hoc): a year that passes its own test but whose every comparison with a
    neighbouring year was refused would stand alone as a level without context; refuse it too."""
    pairs: dict[tuple[str, str], list[tuple[list[str], bool]]] = {}
    for ind, clock, per, _, failed in rows:
        if len(per) == 2:
            pairs.setdefault((ind, clock), []).append((per, not failed))
    out = []
    for ind, clock, per, measures, failed in rows:
        if len(per) == 1 and not failed:
            mine = [(p, ok) for p, ok in pairs.get((ind, clock), []) if per[0] in p]
            if mine and not any(ok for _, ok in mine):
                nb = sorted({x for p, _ in mine for x in p if x != per[0]})
                failed = [
                    {
                        "measure": "isolated",
                        "value": None,
                        "text": (
                            f"No neighbouring year is comparable with {per[0]}: the comparison "
                            f"with {' and '.join(nb)} was refused, so a single-year figure would "
                            "stand alone as a level without context."
                        ),
                    }
                ]
        out.append((ind, clock, per, measures, failed))
    return out


def decisions(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """The decisions of the latest Gate 2 run."""
    g = latest_run(con, "gate2")
    if g is None:
        return []
    out = []
    for did, ind, clock, per, passed, reasons in con.execute(
        "SELECT decision_id, indicator, clock, periods, passed, reasons FROM gate_decision"
        " WHERE run_id = ? ORDER BY decision_id",
        [g[0]],
    ).fetchall():
        out.append(
            {
                "id": did, "indicator": ind, "clock": clock, "periods": list(per),
                "passed": passed, "reasons": json.loads(reasons),
            }
        )  # fmt: skip
    return out


def _report(con, cfg, run_id, ind_run, res: Gate2Result, out: Path) -> None:
    th = cfg["comparability"]
    decs = decisions(con)
    lines = [
        "# Gate 2: comparability (ticket C2)",
        f"Run `{run_id}`, on indicators run `{ind_run}`.",
        "",
        "Thresholds were fixed in `gate.toml` before any indicator was computed (D007, D038):",
        (
            f"minimum populatedness {_pct(th['min_populatedness'])}, maximum populatedness spread "
            f"{100 * th['max_populatedness_spread']:.0f} points, volume ratio between "
            f"{th['volume_ratio_band'][0]} and {th['volume_ratio_band'][1]}, maximum composition "
            f"drift {th['max_composition_drift']}."
        ),
        "",
        f"**{res.decisions} decisions: {res.passed} passed, {res.refusals} refused.**",
        "",
        "## Refusals by indicator and clock",
        "",
        "| Indicator | Clock | Decisions | Refused |",
        "|---|---|---|---|",
    ]
    for ind in INDICATORS:
        for clock in CLOCKS:
            ds = [d for d in decs if d["indicator"] == ind and d["clock"] == clock]
            lines.append(
                f"| {LABELS[ind]} | {CLOCK_NAMES[clock]} | {len(ds)} |"
                f" {sum(1 for d in ds if not d['passed'])} |"
            )
    lines += ["", "## Volume ratio between consecutive years", ""]
    lines += ["| Clock | Pair | Records | Ratio | Within band |", "|---|---|---|---|---|"]
    seen = set()
    for d in decs:
        if len(d["periods"]) == 2 and (d["clock"], tuple(d["periods"])) not in seen:
            seen.add((d["clock"], tuple(d["periods"])))
            m = d["reasons"]["measures"]
            ok = th["volume_ratio_band"][0] <= m["volume_ratio"] <= th["volume_ratio_band"][1]
            lines.append(
                f"| {CLOCK_NAMES[d['clock']]} | {d['periods'][0]} to {d['periods'][1]} |"
                f" {m['n_a']:,} to {m['n_b']:,} | {m['volume_ratio']:.2f} | {'yes' if ok else 'no'} |"
            )
    lines += ["", "## Composition drift between consecutive years (CPV division mix)", ""]
    lines += ["| Clock | Pair | Drift | Within limit |", "|---|---|---|---|"]
    seen = set()
    for d in decs:
        if len(d["periods"]) == 2 and (d["clock"], tuple(d["periods"])) not in seen:
            seen.add((d["clock"], tuple(d["periods"])))
            m = d["reasons"]["measures"]
            ok = m["composition_drift"] <= th["max_composition_drift"]
            lines.append(
                f"| {CLOCK_NAMES[d['clock']]} | {d['periods'][0]} to {d['periods'][1]} |"
                f" {m['composition_drift']:.3f} | {'yes' if ok else 'no'} |"
            )
    lines += ["", "## Every refusal, with its reason", ""]
    refused = [d for d in decs if not d["passed"]]
    if not refused:
        lines.append("None: every comparison passed (a finding, not a failure).")
    for d in refused:
        lines.append(f"- {refusal_text(d['indicator'], d['clock'], d['periods'], d['reasons'])}")
    lines += ["", "## Clocks side by side (awarded value, headline)", ""]
    lines += [
        "| Period | Award year | Tender start year | Relative gap | Note |",
        "|---|---|---|---|---|",
    ]
    cap = float(cfg.get("informational", {}).get("max_clock_divergence", 0.25))
    vals = {
        (r[0], r[1]): r[2]
        for r in con.execute(
            "SELECT clock, period, value FROM indicator_value WHERE indicator = 'awarded_value'"
            " AND slice_type = 'all' AND variant = 'headline'"
        ).fetchall()
    }
    for p in sorted({p for (_, p) in vals}):
        a, t = vals.get(("award_year", p)), vals.get(("tender_year", p))
        if a is None or t is None or max(a, t) == 0:
            continue
        gap = abs(a - t) / max(a, t)
        note = "clocks differ by more than the informational limit" if gap > cap else ""
        lines.append(f"| {p} | {a / 1e9:,.2f} bn | {t / 1e9:,.2f} bn | {gap:.2f} | {note} |")
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
