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

## Week 2: entities and facts

```
make entities          # entity table, fact_award, fact_award_supplier, evidence/entities.md
make audit-sample      # writes audit/groups_dev.csv and groups_test.csv
make audit-eval        # after labelling the dev sheet
make regions-sample    # then fill the status column of audit/region_check.csv
make regions-eval
```

See `docs/methodology.md`.

## Week 3: indicators, Gate 2 and the site

```
make pipeline          # entities, indicators, gate, site (after stage and validate)
make site              # just the site, from what passed Gate 2
```

The four indicators are computed on two clocks, the award year and the tender start year (D032),
and every pair of consecutive years is judged against `gate.toml` before a trend is drawn. A failed
judgement is printed on the site in place of the comparison. `site/` is committed on purpose: it has
no timestamp, so `git diff site/` shows exactly which published numbers changed between runs.

CI runs the whole pipeline on the real 2025 file and fails if the gate judged nothing; GitHub Pages
serves the committed `site/` built from the full file (D039). Pages must be set to "GitHub Actions"
as its source in the repository settings.

Method, definitions and limits: `docs/methodology.md`.
