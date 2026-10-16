"""Threshold sensitivity for Gate 2.

The thresholds in gate.toml were fixed before any indicator ran and are not changed here. This
module re-judges the same measurements under other thresholds, in memory, and reports which
judgements would flip. It writes nothing to the database: it is a disclosure of how much the
published result depends on the chosen limits, not a way to tune them."""

from __future__ import annotations

import copy
from pathlib import Path

import duckdb

from appalti.gate2 import CLOCK_NAMES, LABELS, judge_all, load_inputs, load_thresholds
from appalti.indicators import IndicatorsRefused

# One threshold moved at a time, one step each way, then all moved together.
SCENARIOS: list[tuple[str, dict]] = [
    ("baseline (gate.toml)", {}),
    ("min populatedness 0.40", {"min_populatedness": 0.40}),
    ("min populatedness 0.60", {"min_populatedness": 0.60}),
    ("max populatedness spread 0.30", {"max_populatedness_spread": 0.30}),
    ("max populatedness spread 0.10", {"max_populatedness_spread": 0.10}),
    ("volume ratio band 0.33 to 3.0", {"volume_ratio_band": [0.33, 3.0]}),
    ("volume ratio band 0.67 to 1.5", {"volume_ratio_band": [0.67, 1.5]}),
    ("max composition drift 0.10", {"max_composition_drift": 0.10}),
    ("max composition drift 0.20", {"max_composition_drift": 0.20}),
    ("max composition drift 0.25", {"max_composition_drift": 0.25}),
    (
        "all lenient together",
        {
            "min_populatedness": 0.40,
            "max_populatedness_spread": 0.30,
            "volume_ratio_band": [0.33, 3.0],
            "max_composition_drift": 0.25,
        },
    ),
    (
        "all strict together",
        {
            "min_populatedness": 0.60,
            "max_populatedness_spread": 0.10,
            "volume_ratio_band": [0.67, 1.5],
            "max_composition_drift": 0.10,
        },
    ),
]
FOCUS = ("awarded_value", "award_year")


def ranges(years: list[int]) -> str:
    out, i = [], 0
    ys = sorted(years)
    while i < len(ys):
        j = i
        while j + 1 < len(ys) and ys[j + 1] == ys[j] + 1:
            j += 1
        out.append(str(ys[i]) if i == j else f"{ys[i]} to {ys[j]}")
        i = j + 1
    return ", ".join(out) or "none"


def _key(row) -> tuple:
    return (row[0], row[1], tuple(row[2]))


def published(rows: list, indicator: str, clock: str) -> tuple[list[int], list[tuple[int, int]]]:
    """Years that pass on their own and consecutive pairs that pass."""
    years, pairs = [], []
    for ind, clk, per, _, failed in rows:
        if (ind, clk) != (indicator, clock) or failed:
            continue
        if len(per) == 1:
            years.append(int(per[0]))
        else:
            pairs.append((int(per[0]), int(per[1])))
    return years, pairs


def scenario(cfg: dict, change: dict, pop: dict, comp: dict) -> list:
    c = copy.deepcopy(cfg)
    c["comparability"].update(change)
    return judge_all(c, pop, comp)


def margins(base_rows: list, cfg: dict) -> list[dict]:
    """For every pair refused for exactly one measure, how far past the limit it is."""
    th = cfg["comparability"]
    lo, hi = th["volume_ratio_band"]
    out = []
    for ind, clk, per, m, failed in base_rows:
        if len(per) != 2 or len(failed) != 1:
            continue
        f = failed[0]
        v = f["value"]
        if f["measure"] == "composition_drift":
            limit, rel = th["max_composition_drift"], v / th["max_composition_drift"] - 1
            needs = f"drift limit of at least {v:.3f}"
        elif f["measure"] == "volume_ratio":
            if v < lo:
                limit, rel = lo, lo / v - 1
                needs = f"lower ratio bound of at most {v:.2f}"
            else:
                limit, rel = hi, v / hi - 1
                needs = f"upper ratio bound of at least {v:.2f}"
        elif f["measure"] == "populatedness_spread":
            limit, rel = th["max_populatedness_spread"], v / th["max_populatedness_spread"] - 1
            needs = f"spread limit of at least {v:.2f}"
        else:
            continue
        out.append(
            {
                "indicator": ind, "clock": clk, "pair": per, "measure": f["measure"],
                "value": v, "limit": limit, "rel": rel, "needs": needs,
            }
        )  # fmt: skip
    return sorted(out, key=lambda r: r["rel"])


def run(db: Path, gate_path: Path, out: Path) -> dict:
    cfg = load_thresholds(gate_path)
    first, last = int(cfg["window"]["first_period"]), int(cfg["window"]["last_period"])
    con = duckdb.connect(str(db), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        if not {"ind_populatedness", "ind_composition"} <= tables:
            raise IndicatorsRefused("no indicator tables: run `appalti indicators` first")
        pop, comp = load_inputs(con, first, last)
    finally:
        con.close()

    results = [(name, change, scenario(cfg, change, pop, comp)) for name, change in SCENARIOS]
    base = results[0][2]
    base_ok = {_key(r): not r[4] for r in base}
    total = len(base)

    th = cfg["comparability"]
    lines = [
        "# Gate 2: threshold sensitivity",
        "",
        "The thresholds in `gate.toml` were fixed before any indicator was computed and were not",
        "changed after seeing the results. This page re-judges the same measurements under other",
        "limits, in memory, to show how much the published result depends on them. It is a",
        "disclosure, not a tuning step: nothing here is written to `gate_decision` and no limit",
        "was moved because of it.",
        "",
        (
            f"Baseline: minimum populatedness {th['min_populatedness']}, maximum populatedness "
            f"spread {th['max_populatedness_spread']}, volume ratio band "
            f"{th['volume_ratio_band'][0]} to {th['volume_ratio_band'][1]}, maximum composition "
            f"drift {th['max_composition_drift']}. {total} judgements in the window {first} to "
            f"{last}."
        ),
        "",
        "## One limit at a time, then all together",
        "",
        (
            f"The last two columns follow {LABELS[FOCUS[0]].lower()} on the "
            f"{CLOCK_NAMES[FOCUS[1]]} clock, the headline indicator."
        ),
        "",
        "| Scenario | Refused | Judgements that flip | Years shown | Years joined into a line |",
        "|---|---|---|---|---|",
    ]
    details = []
    for name, _, rows in results:
        refused = sum(1 for r in rows if r[4])
        flips = [r for r in rows if base_ok[_key(r)] != (not r[4])]
        years, pairs = published(rows, *FOCUS)
        segs: list[list[int]] = []
        for a, b in pairs:
            if segs and segs[-1][1] == a:
                segs[-1][1] = b
            else:
                segs.append([a, b])
        joined = ", ".join(f"{a} to {b}" for a, b in segs) or "none"
        lines.append(
            f"| {name} | {refused} of {total} | {len(flips)} | {ranges(years)} | {joined} |"
        )
        if name != "baseline (gate.toml)" and flips:
            details.append((name, flips))

    lines += ["", "## What flips, for the headline indicator", ""]
    shown = False
    for name, flips in details:
        mine = [r for r in flips if (r[0], r[1]) == FOCUS and len(r[2]) == 2]
        if not mine:
            continue
        shown = True
        for r in mine:
            was = "passed, now refused" if r[4] else "was refused, now passes"
            lines.append(f"- {name}: {r[2][0]} compared with {r[2][1]} {was}.")
    if not shown:
        lines.append("No pair of the headline indicator flips under any scenario above.")

    lines += [
        "",
        "## Closest calls: pairs refused for exactly one measure",
        "",
        "How far past its limit each single-cause refusal is, and what the limit would have to",
        "be for the pair to pass. A small margin means the refusal depends on the exact limit.",
        "",
        "| Indicator | Clock | Pair | Measure | Value | Limit | Past the limit by | Would need |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ms = margins(base, cfg)
    for m in ms[:12]:
        lines.append(
            f"| {LABELS[m['indicator']]} | {CLOCK_NAMES[m['clock']]} |"
            f" {m['pair'][0]} to {m['pair'][1]} | {m['measure'].replace('_', ' ')} |"
            f" {m['value']:.3f} | {m['limit']:.3f} | {100 * m['rel']:.0f}% | {m['needs']} |"
        )
    if not ms:
        lines.append("| none | | | | | | | |")

    lines += ["", "## Closest calls: pairs that passed", ""]
    lines += [
        "Drift and volume ratio of the passed pairs of the headline indicator, nearest to a limit.",
        "",
        "| Clock | Pair | Drift | Drift limit | Volume ratio | Band |",
        "|---|---|---|---|---|---|",
    ]
    passed = [
        r for r in base
        if (r[0], r[1]) == (FOCUS[0], FOCUS[1]) and len(r[2]) == 2 and not r[4]
    ]  # fmt: skip
    lo, hi = th["volume_ratio_band"]

    def nearest(r) -> float:
        m = r[3]
        return min(
            (th["max_composition_drift"] - m["composition_drift"]) / th["max_composition_drift"],
            (m["volume_ratio"] - lo) / lo,
            (hi - m["volume_ratio"]) / hi,
        )

    passed.sort(key=nearest)
    for r in passed[:6]:
        m = r[3]
        lines.append(
            f"| {CLOCK_NAMES[r[1]]} | {r[2][0]} to {r[2][1]} | {m['composition_drift']:.3f} |"
            f" {th['max_composition_drift']} | {m['volume_ratio']:.2f} | {lo} to {hi} |"
        )
    if not passed:
        lines.append("| none | | | | | |")
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return {"scenarios": len(results), "judgements": total, "closest": ms[:1]}
