"""SVG charts as plain strings (D004: no JavaScript, no CDN). Colours come from CSS variables so
the page's light and dark themes apply; marks use thin strokes, direct labels and a legend, and
every chart is paired with a table view by the caller. Tooltips are native <title> elements."""

from __future__ import annotations

import itertools
import math
from html import escape

W, H = 680, 320
ML, MR, MT, MB = 64, 104, 20, 44


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * p:
            return m * p
    return 10 * p


def _fmt(v: float, unit: str, dec: int = 1) -> str:
    if unit == "bn":
        return f"{v:,.{dec}f} bn"
    if unit == "pct":
        return f"{100 * v:.0f}%"
    return f"{v:,.2f}"


def _frame(title: str, body: str, desc: str, h: int = H) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(title)}"'
        f"><title>{escape(title)}</title>"
        f"<desc>{escape(desc)}</desc>{body}</svg>"
    )


def _axes(periods: list[int], ymax: float, unit: str, xs, h: int = H, mb: int = MB) -> str:
    out = []
    step = ymax / 4
    dec = 0 if step >= 10 else 1 if step >= 1 else min(4, math.ceil(-math.log10(step)) + 1)
    for i in range(5):
        v = ymax * i / 4
        y = MT + (h - MT - mb) * (1 - i / 4)
        out.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(
            f'<text class="tick" x="{ML - 8}" y="{y + 4:.1f}" text-anchor="end">{_fmt(v, unit, dec)}</text>'
        )
    for p in periods:
        out.append(
            f'<text class="tick" x="{xs(p):.1f}" y="{h - mb + 18}" text-anchor="middle">{p}</text>'
        )
    out.append(f'<line class="axis" x1="{ML}" x2="{W - MR}" y1="{h - mb}" y2="{h - mb}"/>')
    return "".join(out)


def _legend(items: list[tuple[str, str]]) -> str:
    x, out = ML, []
    for cls, name in items:
        out.append(
            f'<rect class="swatch {cls}" x="{x}" y="{H - 14}" width="10" height="10" rx="2"/>'
            f'<text class="legend" x="{x + 14}" y="{H - 5}">{escape(name)}</text>'
        )
        x += 28 + 6.2 * len(name)
    return "".join(out)


def line_chart(
    title: str,
    periods: list[int],
    series: list[dict],
    unit: str = "bn",
    desc: str = "",
) -> str:
    """series: [{name, cls, values: {period: value}, shown: set(periods), joined: set(periods)}]
    A segment p -> p+1 is drawn only if p+1 is in `joined`; a point only if its period is in
    `shown`. Periods not in `shown` get an 'n/p' (not published) mark on the baseline."""
    vals = [v for s in series for p, v in s["values"].items() if p in s["shown"] and v is not None]
    ymax = _nice_max(max(vals) if vals else 1.0)
    span = max(1, len(periods) - 1)

    def xs(p):
        return ML + (W - ML - MR) * (periods.index(p) / span)

    def ys(v):
        return MT + (H - MT - MB) * (1 - v / ymax)

    body = [_axes(periods, ymax, unit, xs)]
    taken: list[float] = []
    for s in series:
        pts = [(p, s["values"].get(p)) for p in periods]
        for (p0, v0), (p1, v1) in itertools.pairwise(pts):
            if (
                p0 in s["shown"] and p1 in s["shown"] and p1 in s["joined"]
                and v0 is not None and v1 is not None
            ):  # fmt: skip
                body.append(
                    f'<line class="line {s["cls"]}" x1="{xs(p0):.1f}" y1="{ys(v0):.1f}"'
                    f' x2="{xs(p1):.1f}" y2="{ys(v1):.1f}"/>'
                )
        last = None
        for p, v in pts:
            if p in s["shown"] and v is not None:
                body.append(
                    f'<circle class="dot {s["cls"]}" cx="{xs(p):.1f}" cy="{ys(v):.1f}" r="4">'
                    f"<title>{escape(s['name'])}, {p}: {_fmt(v, unit)}</title></circle>"
                )
                last = (p, v)
        if last:
            ly = ys(last[1]) + 4
            while any(abs(ly - t) < 14 for t in taken):
                ly += 14
            taken.append(ly)
            body.append(
                f'<text class="label" x="{xs(last[0]) + 8:.1f}" y="{ly:.1f}">'
                f"{escape(s['name'])}</text>"
            )
    for p in periods:
        if all(p not in s["shown"] for s in series):
            body.append(
                f'<text class="np" x="{xs(p) + 4:.1f}" y="{H - MB - 6}" text-anchor="middle">n/p</text>'
            )
    body.append(_legend([(s["cls"], s["name"]) for s in series]))
    return _frame(title, "".join(body), desc or title)


def band_chart(title: str, periods: list[int], series: list[dict], desc: str = "") -> str:
    """Concentration as a range: each series has {name, cls, low, high, shown, joined}; the band
    between `low` (point) and `high` (upper) is shaded and both edges drawn."""
    vals = [v for s in series for p in s["shown"] for v in (s["low"].get(p), s["high"].get(p))
            if v is not None]  # fmt: skip
    ymax = min(1.0, _nice_max(max(vals) if vals else 1.0))
    span = max(1, len(periods) - 1)

    def xs(p):
        return ML + (W - ML - MR) * (periods.index(p) / span)

    def ys(v):
        return MT + (H - MT - MB) * (1 - v / ymax)

    body = [_axes(periods, ymax, "pct", xs)]
    for s in series:
        run = []
        runs = []
        for p in periods:
            ok = p in s["shown"] and s["low"].get(p) is not None
            if ok and (not run or p in s["joined"]):
                run.append(p)
            else:
                if run:
                    runs.append(run)
                run = [p] if ok else []
        if run:
            runs.append(run)
        for r in runs:
            if len(r) > 1:
                top = " ".join(f"{xs(p):.1f},{ys(s['high'][p]):.1f}" for p in r)
                bot = " ".join(f"{xs(p):.1f},{ys(s['low'][p]):.1f}" for p in reversed(r))
                body.append(f'<polygon class="band {s["cls"]}" points="{top} {bot}"/>')
                for edge in ("high", "low"):
                    pts = " ".join(f"{xs(p):.1f},{ys(s[edge][p]):.1f}" for p in r)
                    body.append(f'<polyline class="line {s["cls"]}" fill="none" points="{pts}"/>')
        for p in periods:
            if p in s["shown"] and s["low"].get(p) is not None:
                lo, hi = s["low"][p], s["high"][p]
                body.append(
                    f'<circle class="dot {s["cls"]}" cx="{xs(p):.1f}" cy="{ys(lo):.1f}" r="4">'
                    f"<title>{escape(s['name'])}, {p}: {_fmt(lo, 'pct')} to {_fmt(hi, 'pct')}"
                    f"</title></circle>"
                )
    for p in periods:
        if all(p not in s["shown"] for s in series):
            body.append(
                f'<text class="np" x="{xs(p) + 4:.1f}" y="{H - MB - 6}" text-anchor="middle">n/p</text>'
            )
    body.append(_legend([(s["cls"], s["name"]) for s in series]))
    return _frame(title, "".join(body), desc or title)


def stacked_bars(
    title: str,
    periods: list[int],
    classes: list[tuple[str, str]],
    shares: dict[tuple[int, str], float],
    shown: set[int],
    desc: str = "",
) -> str:
    """classes: [(key, label)] in fixed order, painted with slots s1..; shares in 0..1."""
    hh, mb = H + 36, MB + 36  # two legend rows under the axis
    n = len(periods)
    bw = min(48.0, (W - ML - MR) / n * 0.62)

    def xc(i):
        return ML + (W - ML - MR) * (i + 0.5) / n

    def ys(v):
        return MT + (hh - MT - mb) * (1 - v)

    body = [_axes([], 1.0, "pct", lambda p: 0, hh, mb)]
    for i, p in enumerate(periods):
        body.append(
            f'<text class="tick" x="{xc(i):.1f}" y="{hh - mb + 18}" text-anchor="middle">{p}</text>'
        )
        if p not in shown:
            body.append(
                f'<text class="np" x="{xc(i):.1f}" y="{hh - mb - 6}" text-anchor="middle">n/p</text>'
            )
            continue
        base = 0.0
        for k, (key, label) in enumerate(classes):
            v = shares.get((p, key), 0.0) or 0.0
            if v <= 0:
                continue
            top = ys(base + v)
            h = ys(base) - top
            body.append(
                f'<rect class="seg s{k + 1}" x="{xc(i) - bw / 2:.1f}" y="{top:.1f}"'
                f' width="{bw:.1f}" height="{max(h, 0):.1f}"><title>{p}, {escape(label)}:'
                f" {100 * v:.1f}%</title></rect>"
            )
            base += v
    items = [(f"s{k + 1}", label) for k, (_, label) in enumerate(classes)]
    legend, x, y = [], ML, hh - 30
    for cls, name in items:
        w = 30 + 5.6 * len(name)
        if x + w > W - 8:
            x, y = ML, y + 15
        legend.append(
            f'<rect class="swatch {cls}" x="{x}" y="{y}" width="10" height="10" rx="2"/>'
            f'<text class="legend" x="{x + 14}" y="{y + 9}">{escape(name)}</text>'
        )
        x += w
    body.append("".join(legend))
    return _frame(title, "".join(body), desc or title, hh)


def ratio_chart(
    title: str,
    pairs: list[str],
    series: list[dict],
    band: tuple[float, float],
    desc: str = "",
) -> str:
    """Volume ratios on a log scale. series: [{name, cls, values: {pair: ratio}}]. A point inside
    the accepted band is a filled circle; outside it, a hollow ring labelled 'outside'."""
    lo_v, hi_v = 1 / 64, 8.0
    allv = [v for s in series for v in s["values"].values() if v > 0]
    if allv:
        lo_v, hi_v = min(lo_v, min(allv) / 1.5), max(hi_v, max(allv) * 1.5)
    lg0, lg1 = math.log2(lo_v), math.log2(hi_v)
    n = len(pairs)

    def xc(i):
        return ML + (W - ML - MR) * (i + 0.5) / n

    def ys(v):
        return MT + (H - MT - MB) * (1 - (math.log2(v) - lg0) / (lg1 - lg0))

    body = []
    body.append(
        f'<rect class="okband" x="{ML}" y="{ys(band[1]):.1f}" width="{W - ML - MR}"'
        f' height="{ys(band[0]) - ys(band[1]):.1f}"/>'
    )
    g = 1 / 64
    while g <= hi_v * 1.01:
        if g >= lo_v:
            body.append(
                f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{ys(g):.1f}" y2="{ys(g):.1f}"/>'
            )
            lab = f"{g:g}" if g >= 1 / 16 else f"1/{round(1 / g)}"
            body.append(
                f'<text class="tick" x="{ML - 8}" y="{ys(g) + 4:.1f}" text-anchor="end">{lab}</text>'
            )
        g *= 2
    body.append(
        f'<text class="np" x="{W - MR + 6}" y="{ys(band[1]) + 12:.1f}">accepted band</text>'
        f'<text class="np" x="{W - MR + 6}" y="{ys(band[0]) - 4:.1f}">{band[0]} to {band[1]}</text>'
    )
    for i, pr in enumerate(pairs):
        body.append(
            f'<text class="tick" x="{xc(i):.1f}" y="{H - MB + 18}" text-anchor="middle">{pr}</text>'
        )
    off = 9
    for k, s in enumerate(series):
        dx = (k - (len(series) - 1) / 2) * 2 * off
        for i, pr in enumerate(pairs):
            v = s["values"].get(pr)
            if not v or v <= 0:
                continue
            out = not band[0] <= v <= band[1]
            cls = f"dot {s['cls']}" + (" ring" if out else "")
            body.append(
                f'<circle class="{cls}" cx="{xc(i) + dx:.1f}" cy="{ys(v):.1f}" r="5">'
                f"<title>{escape(s['name'])}, {pr}: {v:.2f}"
                f"{' (outside the band)' if out else ''}</title></circle>"
            )
    body.append(_legend([(s["cls"], s["name"]) for s in series]))
    return _frame(title, "".join(body), desc or title)
