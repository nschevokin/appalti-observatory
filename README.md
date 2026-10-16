# appalti-observatory

An analytics pipeline that refuses to publish numbers it cannot justify.

It loads 562,862 Italian public tenders above 40,000 euro (ANAC data, OCDS format), resolves the
companies and public bodies behind them, computes four procurement indicators on two clocks, and
publishes them as a static site. Two gates decide what may be shown:

- **Gate 1 (ingestion).** Records that fail validation are excluded and counted: 5,165 of 562,886
  processes (0.92%). The load aborts if more than 2% fail.
- **Gate 2 (comparability).** Before two consecutive years are joined in a chart, they are tested
  against thresholds fixed in `gate.toml` before the data was judged: how complete the field is,
  how much the number of records changed, how much the sector mix shifted. A failed comparison is
  not drawn. The site prints the reason instead.

**Live site:** https://nschevokin.github.io/appalti-observatory/

## What the pipeline found

Gate 2 refused 70 of 112 judgements on the full file. For awarded value by award year, 2018 to
2020 are joined and 2021 to 2022 are joined, but 2020 to 2021 is not: the sector mix shifted by
0.161 against a limit of 0.15. That is a narrow miss, and the threshold was not changed to avoid
it. 2023 onward is refused because the record count falls to a fraction of 2022 (0.26, 0.03, 0.07).
The single-bidder share is refused for every year because the tenderer-count field is empty in the
source. Every figure on the site is traceable to a file in `evidence/`.

Two rules were added after the first full run and are recorded as post hoc: the isolated-year rule
(D040) and the award-year clock (D015). Decisions are in `docs/decisions.md`; entries are never
edited.

## Limits and non-claims

- Awarded is not spent. Execution and payment sections of the source are empty, and contracts are
  amended, cancelled and underspent.
- This is not all public procurement: the 40,000 euro threshold removes everything below it.
- A single bidder is not evidence of wrongdoing, and no page names or ranks a buyer or supplier.
- Entity resolution is an identifier join. The audit (`evidence/audit_dev.md`) estimated that about
  7% of multi-id names split one entity (wide interval, 13 decided pairs); concentration is
  therefore shown as a range. Labels in the audit were drafted by Claude from the sheet alone and
  reviewed by the author; the test split is unopened.
- A joined line means the years are comparable, not that a change is explained.
- Single-node batch processing over a frozen dataset: no streaming, orchestration or concurrency.

## Reproduce

```
uv sync
make fetch-full        # fetches the full file and pins its sha256 in manifest.json
make stage validate    # Gate 1
make pipeline          # entities, indicators, Gate 2, site
```

Stages refuse to run if the input file's hash differs from the manifest. `site/` is committed on
purpose: it has no timestamp, so `git diff site/` shows exactly which published numbers changed.
CI (`.github/workflows/ci.yml`) lints, runs the tests, then runs the whole pipeline on the real 2025
file and fails if Gate 2 judged nothing; Pages publishes the committed `site/` (D039).

Method and definitions: `docs/methodology.md`. Audit of the entity join: `docs/methodology.md`,
week 2.

## Attribution and licence

Source: contract data published by ANAC (Autorità Nazionale Anticorruzione), obtained via the Open
Contracting Partnership data registry, licensed CC BY 4.0. Analysis and any errors are the
author's own. Code: MIT (`LICENSE`). The data keeps its own licence.
