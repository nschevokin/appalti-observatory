# appalti-observatory

An analytics pipeline that refuses to publish numbers it cannot justify.

It loads Italian public contracts above 40,000 euro (2020 to September 2025), resolves the companies and public bodies behind them, computes four procurement indicators, and publishes them as a static site. Entity resolution is scored against a hand-labelled sample, and a cross-period comparison whose underlying coverage shifted too much is not published: the site prints the reason instead of the chart.

**Status:** day 1 (reconnaissance). Start with `docs/recon.md`.

## Day-1 quickstart

```
uv sync
make recon-sample     # smoke test on a synthetic file
git add -A && git commit -m "Recon decision rules before running queries"
make fetch-full       # 184 MB
make recon            # writes docs/recon_output.md
```

## Attribution

Source: contract data published by ANAC (Autorità Nazionale Anticorruzione), obtained via the Open Contracting Partnership data registry, licensed CC BY 4.0. Analysis and any errors are the author's own.

## Limits (to be completed in C5)

Awarded is not spent. The 40,000 euro threshold means this is not all public procurement. A single bidder is not evidence of wrongdoing. Single-node batch processing over a frozen dataset: no streaming, orchestration or concurrency.

## Storage trade-off

DuckDB's constraint enforcement is weaker than PostgreSQL's, so the publication gate lives in application code with an append-only `gate_decision` table behind it, not in foreign keys.
