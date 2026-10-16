"""Ticket C3: render site/ from what passed Gate 2. Reads only the database and the evidence
folder; the output has no timestamp, so the git diff between runs shows exactly which published
numbers changed (D005). Charts are SVG strings from charts.py; there is no JavaScript."""

from __future__ import annotations

import re
import shutil
from html import escape
from pathlib import Path

import duckdb

from appalti import charts
from appalti.gate2 import CLOCK_NAMES, LABELS, decisions, refusal_text
from appalti.indicators import CLOCKS, latest_run
from appalti.stage import _connect

CLASS_LABELS = {
    "open_or_restricted": "Open or restricted",
    "negotiated_with_notice": "Negotiated, with notice",
    "negotiated_without_notice": "Negotiated, without notice",
    "below_threshold": "Below threshold",
    "direct_award": "Direct award",
    "framework_call_off": "Framework call-off",
    "other": "Other",
}
CLASS_ORDER = list(CLASS_LABELS)
CHART_NAMES = {"award_year": "Award year", "tender_year": "Tender year"}
EVIDENCE_FILES = [
    "stage_reconciliation.md", "gate1_rejects.md", "coverage.md", "entities.md",
    "audit_dev.md", "region_check.md", "indicators.md", "gate2.md",
]  # fmt: skip
PAGES = [
    ("index.html", "Overview"),
    ("awarded-value.html", "Awarded value"),
    ("concentration.html", "Concentration"),
    ("procedure-mix.html", "Procedure mix"),
    ("single-bidder.html", "Single bidder"),
    ("comparability.html", "Comparability"),
    ("quality.html", "Data quality"),
    ("method.html", "Method"),
]

CSS = """
:root{color-scheme:light;--surface:#fcfcfb;--panel:#f3f2ee;--text:#0b0b0b;--text2:#52514e;
--muted:#6b6a66;--grid:#e4e3df;--axis:#b9b8b2;--accent:#184f95;--warn-bg:#fdf3e3;--warn:#8a4b00;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;}
@media (prefers-color-scheme: dark){:root{color-scheme:dark;--surface:#1a1a19;--panel:#242422;
--text:#f0efec;--text2:#c3c2b7;--muted:#9c9b95;--grid:#34332f;--axis:#5b5a55;--accent:#86b6ef;
--warn-bg:#2b2316;--warn:#f0c27a;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;
--s5:#d55181;--s6:#008300;--s7:#9085e9;}}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);
font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
header,main,footer{max-width:760px;margin:0 auto;padding:0 16px}
header{padding-top:20px}nav{display:flex;flex-wrap:wrap;gap:4px 14px;margin:8px 0 24px;
font-size:14px}nav a{color:var(--text2);text-decoration:none;padding:2px 0;
border-bottom:2px solid transparent}nav a[aria-current]{color:var(--text);border-color:var(--accent)}
h1{font-size:28px;line-height:1.2;margin:8px 0 12px}h2{font-size:20px;margin:32px 0 8px}
p,li{max-width:68ch}a{color:var(--accent)}
.lede{font-size:18px;color:var(--text2)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}
.tile{background:var(--panel);border-radius:8px;padding:12px 14px}
.tile b{display:block;font-size:26px;line-height:1.2}.tile span{font-size:13px;color:var(--text2)}
.refusal{background:var(--warn-bg);border-left:4px solid var(--warn);padding:12px 16px;
margin:16px 0;border-radius:4px}.refusal p{margin:6px 0}.refusal strong{color:var(--warn)}
.note{background:var(--panel);padding:10px 14px;border-radius:6px;font-size:14px;margin:16px 0}
figure{margin:20px 0}figcaption{font-size:13px;color:var(--text2)}
svg.chart{width:100%;height:auto;display:block}
.chart text{fill:var(--text2);font:12px system-ui,sans-serif}.chart .label{fill:var(--text)}
.chart .np{fill:var(--muted);font-size:11px}.chart .legend{fill:var(--text2)}
.chart .grid{stroke:var(--grid);stroke-width:1}.chart .axis{stroke:var(--axis);stroke-width:1}
.chart .line{stroke-width:2;fill:none}.chart .dot{stroke:var(--surface);stroke-width:2}
.chart .dot.ring{fill:var(--surface);stroke-width:2.5}.chart .okband{fill:var(--panel)}
.chart .band{opacity:.22;stroke:none}.chart .seg{stroke:var(--surface);stroke-width:2}
.s1{fill:var(--s1);stroke:var(--s1)}.s2{fill:var(--s2);stroke:var(--s2)}
.s3{fill:var(--s3);stroke:var(--s3)}.s4{fill:var(--s4);stroke:var(--s4)}
.s5{fill:var(--s5);stroke:var(--s5)}.s6{fill:var(--s6);stroke:var(--s6)}
.s7{fill:var(--s7);stroke:var(--s7)}
.chart .line.s1,.chart .line.s2,.chart .line.s3,.chart .line.s4{fill:none}
.chart .dot.ring.s1{stroke:var(--s1)}.chart .dot.ring.s2{stroke:var(--s2)}
.chart .dot.ring.s3{stroke:var(--s3)}.chart .dot.ring.s4{stroke:var(--s4)}
.chart .swatch{stroke:none}
.chart .seg{stroke:var(--surface)}.chart .seg.s1,.chart .seg.s2,.chart .seg.s3,.chart .seg.s4,
.chart .seg.s5,.chart .seg.s6,.chart .seg.s7{stroke:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}
th,td{text-align:right;padding:4px 8px;border-bottom:1px solid var(--grid)}
th:first-child,td:first-child{text-align:left}th{color:var(--text2);font-weight:600}
td.l{text-align:left}details{margin:8px 0}summary{cursor:pointer;color:var(--text2);font-size:14px}
footer{font-size:13px;color:var(--text2);padding-bottom:40px;margin-top:40px;
border-top:1px solid var(--grid);padding-top:16px}code{font-size:.9em}
@media(max-width:560px){h1{font-size:24px}}
"""

NONCLAIMS = """<div class="note"><strong>What these figures do not mean.</strong>
<em>Awarded</em> is not <em>spent</em>: the planning, documents and transactions sections of the
data are empty, so execution and payment are invisible, and contracts are amended, cancelled and
underspent. This is not all public procurement: the threshold is 40,000 euro, so everything below
it is absent. A single bidder is not evidence of wrongdoing; it has ordinary explanations such as
specialised goods, emergencies, small regional markets and framework call-offs. No page names or
ranks a buyer or supplier by any risk indicator.</div>"""


class SiteRefused(Exception):
    """Gate 2 has produced no decisions: nothing may be published."""


def _bn(v: float | None) -> str:
    return "n/a" if v is None else f"{v / 1e9:,.1f} bn"


def _pct(v: float | None, d: int = 1) -> str:
    return "n/a" if v is None else f"{100 * v:.{d}f}%"


class Data:
    def __init__(self, con: duckdb.DuckDBPyConnection, evidence: Path) -> None:
        self.con = con
        self.evidence = evidence
        g = latest_run(con, "gate2")
        i = latest_run(con, "indicators")
        e = latest_run(con, "entities")
        if g is None or i is None:
            raise SiteRefused("no indicators or Gate 2 run: nothing to publish")
        self.gate_run, self.ind_run, self.sha = g[0], i[0], g[1]
        self.ent_run = e[0] if e else "n/a"
        self.decs = decisions(con)
        if not self.decs:
            raise SiteRefused("gate_decision has no rows: the pipeline ran without judging")
        self.values: dict[tuple, tuple[float | None, int]] = {}
        for ind, clock, period, st, sv, var, val, n in con.execute(
            "SELECT indicator, clock, period, slice_type, slice_value, variant, value, n"
            " FROM indicator_value"
        ).fetchall():
            self.values[(ind, clock, period, st, sv, var)] = (val, n)
        self.pop = {
            (r[0], r[1], r[2]): (r[3], r[4])
            for r in con.execute(
                "SELECT indicator, clock, period, n, n_populated FROM ind_populatedness"
            ).fetchall()
        }
        self.periods = sorted({k[2] for k in self.values})
        self.lines = int(con.execute("SELECT count(*) FROM stg_release").fetchone()[0])
        self.rejected = int(
            con.execute("SELECT processes FROM gate1_summary WHERE reason = 'ALL'").fetchone()[0]
        )
        self.gate1 = con.execute(
            "SELECT reason, rows, processes FROM gate1_summary WHERE reason <> 'ALL' ORDER BY 3 DESC"
        ).fetchall()

    def shown(self, indicator: str, clock: str) -> set[int]:
        return {
            int(d["periods"][0])
            for d in self.decs
            if d["indicator"] == indicator and d["clock"] == clock
            and len(d["periods"]) == 1 and d["passed"]
        }  # fmt: skip

    def joined(self, indicator: str, clock: str) -> set[int]:
        return {
            int(d["periods"][1])
            for d in self.decs
            if d["indicator"] == indicator and d["clock"] == clock
            and len(d["periods"]) == 2 and d["passed"]
        }  # fmt: skip

    def refusals(self, indicator: str | None = None) -> list[dict]:
        return [d for d in self.decs if not d["passed"] and (indicator in (None, d["indicator"]))]

    def audit_line(self) -> str | None:
        f = self.evidence / "audit_dev.md"
        if not f.exists():
            return None
        m = re.search(r"\*\*(\d+\.\d)%\*\* \(95% interval ([\d.]+)% to ([\d.]+)%", f.read_text())
        return None if not m else f"{m.group(1)}% (95% interval {m.group(2)}% to {m.group(3)}%)"


def _refusal_html(d: Data, ds: list[dict], visible: int = 4) -> str:
    if not ds:
        return (
            '<div class="note">Every comparison on this page passed Gate 2. That is a finding,'
            " not a failure: the thresholds were fixed before the data was seen.</div>"
        )

    def block(x: dict) -> str:
        t = refusal_text(x["indicator"], x["clock"], x["periods"], x["reasons"])
        head, _, rest = t.partition(": not published.")
        return f"<p><strong>{escape(head.strip())}: not published.</strong>{escape(rest)}</p>"

    shown = "".join(block(x) for x in ds[:visible])
    more = ""
    if len(ds) > visible:
        more = (
            f"<details><summary>{len(ds) - visible} more refusals</summary>"
            + "".join(block(x) for x in ds[visible:])
            + "</details>"
        )
    return f'<aside class="refusal">{shown}{more}</aside>'


def _layout(d: Data, current: str, title: str, body: str) -> str:
    nav = "".join(
        f'<a href="{href}"{" aria-current=page" if href == current else ""}>{escape(label)}</a>'
        for href, label in PAGES
    )
    pct = 100 * d.rejected / d.lines if d.lines else 0.0
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)} · Appalti Observatory</title><style>{CSS}</style></head><body>"
        f"<header><div style='font-size:14px;color:var(--text2)'>Appalti Observatory</div>"
        f"<nav>{nav}</nav></header><main><h1>{escape(title)}</h1>{body}"
        f"{NONCLAIMS}"
        f'<p class="note">Gate 1 excluded {d.rejected:,} of {d.lines:,} processes ({pct:.2f}%) '
        f"before any figure here was computed. The exclusion is concentrated in a small set of "
        f'buyers and is counted on the <a href="quality.html">data quality</a> page.</p></main>'
        f"<footer>Data: Italian ANAC procurement records via the Open Contracting Partnership "
        f"(CC BY 4.0). Code: MIT. Input sha256 <code>{d.sha[:16]}…</code>, indicators run "
        f"<code>{d.ind_run}</code>, Gate 2 run <code>{d.gate_run}</code>. Every figure traces to "
        f'<a href="evidence/indicators.md">evidence/indicators.md</a> and '
        f'<a href="evidence/gate2.md">evidence/gate2.md</a>.</footer></body></html>'
    )


def _table(head: list[str], rows: list[list[str]]) -> str:
    h = "".join(f"<th>{escape(x)}</th>" for x in head)
    r = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table>"


def _fig(svg: str, caption: str, head: list[str], rows: list[list[str]]) -> str:
    return (
        f"<figure>{svg}<figcaption>{escape(caption)}</figcaption>"
        f"<details><summary>Table view</summary>{_table(head, rows)}</details></figure>"
    )


def _window(d: Data) -> list[int]:
    return [p for p in d.periods]


def page_value(d: Data) -> str:
    per = _window(d)
    series = []
    for clock, cls in zip(CLOCKS, ("s1", "s2"), strict=True):
        vals = {p: d.values.get(("awarded_value", clock, p, "all", "all", "headline"), (None, 0))[0]
                for p in per}  # fmt: skip
        series.append(
            {
                "name": CHART_NAMES[clock],
                "cls": cls,
                "values": {p: (v / 1e9 if v is not None else None) for p, v in vals.items()},
                "shown": d.shown("awarded_value", clock),
                "joined": d.joined("awarded_value", clock),
            }
        )
    svg = charts.line_chart(
        "Awarded value per year, billion EUR (headline)", per, series, "bn",
        "Headline awarded value per year on two clocks; years that failed Gate 2 are not drawn.",
    )  # fmt: skip
    rows = []
    for p in per:
        row = [str(p)]
        for clock in CLOCKS:
            v, n = d.values.get(("awarded_value", clock, p, "all", "all", "headline"), (None, 0))
            a = d.values.get(("awarded_value", clock, p, "all", "all", "all"), (None, 0))[0]
            fn = d.values.get(("awarded_value", clock, p, "all", "all", "flagged"), (None, 0))[1]
            row += [_bn(v), f"{n:,}", _bn(a), f"{fn:,}"]
        rows.append(row)
    head = ["Year"] + [
        f"{CLOCK_NAMES[c].capitalize()}: {x}"
        for c in CLOCKS
        for x in ("headline", "awards", "all awards", "flagged awards")
    ]
    last = max(
        (
            p
            for p in d.shown("awarded_value", "award_year")
            if p in d.joined("awarded_value", "award_year")
        ),
        default=None,
    )
    reg = ""
    if last:
        rr = sorted(
            (
                (sv, v, n)
                for (ind, clock, p, st, sv, var), (v, n) in d.values.items()
                if ind == "awarded_value" and clock == "award_year" and p == last
                and st == "region" and v is not None
            ),
            key=lambda x: -x[1],
        )  # fmt: skip
        tot = sum(x[1] for x in rr) or 1
        reg = (
            f"<h2>By buyer region, {last}</h2><p>The buyer's region comes from the postal code "
            "(D026). Regions are aggregates; no buyer is named.</p>"
            + _table(
                ["Region", "Awarded value", "Share", "Awards"],
                [[escape(s), _bn(v), _pct(v / tot), f"{n:,}"] for s, v, n in rr],
            )
        )
    body = (
        '<p class="lede">The euro value of awards made each year, on two clocks: the year the award '
        "was dated, and the year the tender opened.</p>"
        + _fig(
            svg,
            "Source: evidence/indicators.md. Headline excludes processes whose awards sum to more than 10 times the tender amount (D025); the table shows both treatments.",
            head,
            rows,
        )
        + _refusal_html(d, d.refusals("awarded_value"))
        + reg
    )
    return _layout(d, "awarded-value.html", "Awarded value", body)


def page_concentration(d: Data) -> str:
    per = _window(d)
    figs = []
    audit = d.audit_line()
    for clock, cls in zip(CLOCKS, ("s1", "s2"), strict=True):
        low = {
            p: d.values.get(("concentration", clock, p, "all", "all", "point"), (None, 0))[0]
            for p in per
        }
        high = {
            p: d.values.get(("concentration", clock, p, "all", "all", "merged_upper"), (None, 0))[0]
            for p in per
        }
        svg = charts.band_chart(
            f"Top-five supplier share, {CLOCK_NAMES[clock]}", per,
            [{"name": "Top five share", "cls": cls, "low": low, "high": high,
              "shown": d.shown("concentration", clock), "joined": d.joined("concentration", clock)}],
            "Share of headline awarded value held by the five largest suppliers, as a range.",
        )  # fmt: skip
        rows = [
            [
                str(p),
                _pct(low[p]),
                _pct(high[p]),
                f"{d.values.get(('concentration', clock, p, 'all', 'all', 'point'), (None, 0))[1]:,}",
            ]
            for p in per
        ]
        figs.append(
            f"<h2>{CLOCK_NAMES[clock].capitalize()} clock</h2>"
            + _fig(
                svg,
                "The band runs from the identifier-based figure up to the figure with same-name ids merged. Source: evidence/indicators.md.",
                ["Year", "Point", "Upper", "Awards used"],
                rows,
            )
        )
    note = (
        f"Entity resolution is an identifier join. The audit estimated that the identifier splits "
        f"one entity in {audit} of multi-id names, so the true share lies inside the band."
        if audit
        else "The entity audit has not been run; the band is the only guide to uncertainty."
    )
    body = (
        '<p class="lede">How much of each year\'s awarded value went to its five largest suppliers.'
        " Shown as a range because the same company can appear under more than one identifier.</p>"
        f'<div class="note">{escape(note)} Awards without a supplier count in the total but not in '
        "the top five. A supplier named in several tenders is counted once per year.</div>"
        + "".join(figs)
        + _refusal_html(d, d.refusals("concentration"))
    )
    return _layout(d, "concentration.html", "Supplier concentration", body)


def page_mix(d: Data) -> str:
    per = _window(d)
    classes = [
        (k, CLASS_LABELS[k])
        for k in CLASS_ORDER
        if any(key[0] == "procedure_mix" and key[5] == k for key in d.values)
    ]
    figs = []
    for clock in CLOCKS:
        shares = {
            (p, k): d.values.get(("procedure_mix", clock, p, "all", "all", k), (0.0, 0))[0]
            for p in per
            for k, _ in classes
        }
        svg = charts.stacked_bars(
            f"Procedure mix, {CLOCK_NAMES[clock]}", per, classes, shares,
            d.shown("procedure_mix", clock),
            "Share of headline awarded value by type of procedure, per year.",
        )  # fmt: skip
        rows = [[str(p)] + [_pct(shares[(p, k)]) for k, _ in classes] for p in per]
        figs.append(
            f"<h2>{CLOCK_NAMES[clock].capitalize()} clock</h2>"
            + _fig(
                svg,
                "Source: evidence/indicators.md. Classes derive from the procedure code (D023); the mapping is in labels/procedure_class.csv.",
                ["Year"] + [label for _, label in classes],
                rows,
            )
        )
    body = (
        '<p class="lede">What kind of procedure the money went through. Direct awards, framework '
        "call-offs and open procedures behave very differently.</p>"
        + "".join(figs)
        + _refusal_html(d, d.refusals("procedure_mix"))
    )
    return _layout(d, "procedure-mix.html", "Procedure mix", body)


def page_single(d: Data) -> str:
    ds = d.refusals("single_bidder")
    pops = sorted(
        (k[2], v) for k, v in d.pop.items() if k[0] == "single_bidder" and k[1] == "award_year"
    )
    rows = [[str(p), f"{n:,}", f"{npop:,}", _pct(npop / n if n else None)] for p, (n, npop) in pops]
    body = (
        '<p class="lede">The share of awards where the tender had exactly one bidder is a standard '
        "descriptive indicator in procurement research. It cannot be computed from this dataset.</p>"
        + _refusal_html(
            d, [x for x in ds if len(x["periods"]) == 1 and x["clock"] == "award_year"], 2
        )
        + "<p>The record that would carry the count, <code>tender.numberOfTenderers</code>, is "
        "empty in the source. A share computed over all awards instead of awards with a published "
        "count would only measure how complete the publication is, which is why this page shows "
        "nothing rather than a number.</p>"
        + _table(["Year", "Awards", "With a tenderer count", "Populated"], rows)
    )
    return _layout(d, "single-bidder.html", "Single-bidder share: not published", body)


def page_comparability(d: Data) -> str:
    th = d.con.execute(
        "SELECT thresholds FROM gate_decision WHERE run_id = ? LIMIT 1", [d.gate_run]
    ).fetchone()[0]
    import json

    band = json.loads(th)["volume_ratio_band"]
    pairs, series = [], []
    for clock, cls in zip(CLOCKS, ("s1", "s2"), strict=True):
        vals = {}
        for x in d.decs:
            if x["indicator"] == "awarded_value" and x["clock"] == clock and len(x["periods"]) == 2:
                key = f"{x['periods'][0]}→{x['periods'][1][2:]}"
                vals[key] = x["reasons"]["measures"]["volume_ratio"]
                if key not in pairs:
                    pairs.append(key)
        series.append({"name": CHART_NAMES[clock], "cls": cls, "values": vals})
    pairs.sort(key=lambda k: int(k.split("→")[0]))
    svg = charts.ratio_chart(
        "Records in a year divided by records in the year before", pairs, series, tuple(band),
        "Volume ratio per pair of consecutive years, on a log scale, against the accepted band.",
    )  # fmt: skip
    rows = [
        [
            escape(LABELS[x["indicator"]]),
            CLOCK_NAMES[x["clock"]],
            " to ".join(x["periods"]),
            "passed" if x["passed"] else "refused",
            escape(" ".join(f["text"] for f in x["reasons"]["failed"])),
        ]
        for x in d.decs
    ]
    n_ref = len(d.refusals())
    body = (
        '<p class="lede">Before any trend is drawn, each pair of years is judged on three '
        "measures, against thresholds fixed before the data was seen.</p>"
        f"<p>{len(d.decs)} judgements: {len(d.decs) - n_ref} passed, {n_ref} refused.</p>"
        + _fig(
            svg,
            "A hollow ring is a pair outside the accepted band. Source: evidence/gate2.md.",
            ["Pair", "Award year", "Tender start year"],
            [[p] + [f"{s['values'].get(p, float('nan')):.2f}" for s in series] for p in pairs],
        )
        + _refusal_html(d, [x for x in d.refusals() if x["clock"] == "award_year"], 6)
        + "<h2>Every judgement</h2>"
        + _table(["Indicator", "Clock", "Years", "Result", "Reason"], rows).replace(
            "<td>", '<td class="l">'
        )
    )
    return _layout(d, "comparability.html", "Comparability", body)


def page_quality(d: Data) -> str:
    reasons = _table(
        ["Reason", "Rows", "Processes"], [[escape(r), f"{a:,}", f"{b:,}"] for r, a, b in d.gate1]
    )
    reg = d.con.execute(
        "SELECT count(*), count(*) FILTER (WHERE region = 'unknown'),"
        " count(*) FILTER (WHERE award_date_flagged) FROM fact_award"
    ).fetchone()
    pct = 100 * d.rejected / d.lines if d.lines else 0.0
    body = (
        f"<p>The file has {d.lines:,} lines. Gate 1 rejected {d.rejected:,} processes "
        f"({pct:.2f}%), below the 2% limit at which the load aborts. Nothing is dropped silently: "
        "every rejection has a reason code, counted below. One process can fail more than one "
        "rule.</p>"
        + reasons
        + "<h2>Kept but flagged</h2>"
        + f"<p>{reg[2]:,} of {reg[0]:,} awards have an award date outside the validated window and "
        f"are flagged (D014). {reg[1]:,} awards have no usable buyer postal code and sit in region "
        "<em>unknown</em>.</p>"
        '<p>Details: <a href="evidence/gate1_rejects.md">Gate 1</a>, '
        '<a href="evidence/coverage.md">coverage</a>, '
        '<a href="evidence/entities.md">entities</a>, '
        '<a href="evidence/region_check.md">region check</a>.</p>'
    )
    return _layout(d, "quality.html", "Data quality", body)


def page_method(d: Data) -> str:
    body = """
<h2>Question</h2><p>What do Italian public procurement records support saying about how much was
awarded, to whom, and by what procedure, and where do they not?</p>
<h2>Data</h2><p>ANAC records in the Open Contracting Data Standard, via the Open Contracting
Partnership mirror (CC BY 4.0), pinned by sha256. Only tenders above 40,000 euro are present.</p>
<h2>Indicators</h2><ul>
<li><b>Awarded value</b>: sum of award amounts in euro. The headline leaves out processes whose awards
sum to more than ten times the tender amount (D025); the table shows both.</li>
<li><b>Supplier concentration</b>: share of the headline value held by the five largest suppliers.
Awards with several suppliers are split equally (D021). Shown as a range between the identifier join
and a merge of ids sharing a legal-form name.</li>
<li><b>Procedure mix</b>: share of value by class of procedure, from the procedure code (D023).</li>
<li><b>Single-bidder share</b>: awards with one tenderer over awards with a published tenderer count.
Not computable here: the field is empty.</li></ul>
<h2>Two clocks</h2><p>Every indicator is computed on the award year and on the tender start year
(D032). The release year is not used: its counts follow when the publisher loaded records, not when
things happened.</p>
<h2>Gates</h2><p>Gate 1 validates every record at ingestion and publishes the rejection counts. Gate 2
judges each pair of consecutive years on populatedness, volume ratio and composition drift against
thresholds in <code>gate.toml</code>, fixed before any indicator was computed. A refusal is printed
in place of the comparison.</p>
<h2>Entities</h2><p>A supplier is its normalised tax identifier. A hand audit of multi-identifier names
measured how often this splits one company; no merge rule met the pre-registered bar, so none is
applied.</p>
<h2>Limits</h2><ul><li>Awarded, not spent.</li><li>Above-threshold contracts only.</li>
<li>Regions come from postal codes, not from an official field.</li>
<li>Tender and award records can be published late or restated; counts for recent years are
incomplete.</li><li>The audit labels were drafted by an AI assistant and reviewed by the author (D036).
</li></ul>
<p>Full decisions: <a href="https://github.com/nschevokin/appalti-observatory/blob/main/docs/decisions.md">decisions log</a>.</p>"""
    return _layout(d, "method.html", "Method and limits", body)


def page_index(d: Data) -> str:
    refused = d.refusals("awarded_value")
    award_ref = [x for x in refused if x["clock"] == "award_year" and len(x["periods"]) == 2]
    awards = int(d.con.execute("SELECT count(*) FROM fact_award").fetchone()[0])
    total = len(d.decs)
    tiles = (
        f'<div class="tiles"><div class="tile"><b>{awards:,}</b><span>awards analysed</span></div>'
        f'<div class="tile"><b>{d.rejected:,}</b><span>processes rejected at ingestion</span></div>'
        f'<div class="tile"><b>{len(d.refusals()):,} of {total:,}</b><span>comparisons refused by Gate 2</span></div></div>'
    )
    body = (
        '<p class="lede">An analytics pipeline over Italian public procurement records that '
        "refuses to publish numbers it cannot justify.</p>"
        + tiles
        + "<p>Procurement figures are only comparable across years if the underlying records are "
        "similarly complete. Where they are not, a trend measures the publisher, not procurement. "
        "This site computes each indicator, tests every pair of years against thresholds fixed in "
        "advance, and prints the reason when a comparison fails:</p>"
        + _refusal_html(d, award_ref or refused, 2)
        + '<p><a href="comparability.html">All judgements</a> · <a href="method.html">Method and limits</a></p>'
    )
    return _layout(d, "index.html", "What Italian procurement data can and cannot support", body)


def build(db: Path, out_dir: Path, evidence: Path, check_only: bool = False) -> list[str]:
    con = _connect(db)
    try:
        d = Data(con, evidence)
        pages = {
            "index.html": page_index(d),
            "awarded-value.html": page_value(d),
            "concentration.html": page_concentration(d),
            "procedure-mix.html": page_mix(d),
            "single-bidder.html": page_single(d),
            "comparability.html": page_comparability(d),
            "quality.html": page_quality(d),
            "method.html": page_method(d),
        }
    finally:
        con.close()
    if check_only:
        return list(pages)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, html in pages.items():
        (out_dir / name).write_text(html)
    (out_dir / ".nojekyll").write_text("")
    ev = out_dir / "evidence"
    ev.mkdir(exist_ok=True)
    for name in EVIDENCE_FILES:
        src = evidence / name
        if src.exists():
            shutil.copyfile(src, ev / name)
    return list(pages)
