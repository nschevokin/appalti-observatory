RAW ?= data/raw/full.jsonl.gz
URL := https://data.open-contracting.org/en/publication/117/download?name=full.jsonl.gz

.PHONY: fetch-full stage validate coverage entities audit-sample audit-eval audit-confirm regions-sample regions-eval recon recon2 recon3 recon4 recon5 recon6 indicators gate site pipeline recon-sample lint test

# Ticket A2: download (or adopt an existing file) and pin its sha256 in manifest.json.
fetch-full:
	uv run appalti download

# Ticket A3: typed staging tables plus row-count reconciliation (writes evidence/).
stage:
	uv run appalti stage

# Ticket A4: Gate 1, writes rejected_record and evidence/gate1_rejects.md.
validate:
	uv run appalti validate

# Ticket A5: coverage table (append-only) and evidence/coverage.md.
coverage:
	uv run appalti coverage

# Week 2: entities and award facts (needs a passing validate).
entities:
	uv run appalti resolve build

# Draw the audit sample, then label audit/groups_dev.csv by hand.
audit-sample:
	uv run appalti resolve sample

audit-eval:
	uv run appalti resolve eval

# Opens the test split once. A second run is refused.
audit-confirm:
	uv run appalti resolve confirm

# Check the postal-code to region table: fill the status column, then eval.
regions-sample:
	uv run appalti regions sample

regions-eval:
	uv run appalti regions eval

recon:
	uv run python scripts/run_recon.py --raw $(RAW) --out docs/recon_output.md

# Second pass (ticket A1b): identifier quality, consortia, award tail, coding populatedness
recon2:
	uv run python scripts/run_recon.py --sql sql/recon/recon2.sql --raw $(RAW) --db data/recon.duckdb --reuse-raw --out docs/recon2_output.md

# Third pass (ticket A1c): award vs tender, id padding, addresses, procedure mix
recon3:
	uv run python scripts/run_recon.py --sql sql/recon/recon3.sql --raw $(RAW) --db data/recon.duckdb --reuse-raw --out docs/recon3_output.md

# Fourth pass: why buyer references fail Gate 1 (counts only, reads the staged database)
recon4:
	uv run python scripts/run_recon.py --sql sql/recon/recon4.sql --raw $(RAW) --db data/appalti.duckdb --reuse-raw --out docs/recon4_output.md

# Fifth pass: procedure codes with titles (D023) and the unknown-region awards (needs make entities)
recon5:
	uv run python scripts/run_recon.py --sql sql/recon/recon5.sql --raw $(RAW) --db data/appalti.duckdb --reuse-raw --out docs/recon5_output.md

# Sixth pass: shapes of the postal codes that are not five digits (needs make entities)
recon6:
	uv run python scripts/run_recon.py --sql sql/recon/recon6.sql --raw $(RAW) --db data/appalti.duckdb --reuse-raw --out docs/recon6_output.md

# Week 3: indicators (C1), Gate 2 (C2), site (C3)
indicators:
	uv run appalti indicators

gate:
	uv run appalti gate check

site:
	uv run appalti site build

# Everything after validate, in order
pipeline: entities indicators gate site

# Smoke test of the queries on a tiny synthetic file
recon-sample:
	uv run python scripts/run_recon.py --raw tests/fixtures/ocds_sample.jsonl --out /tmp/recon_sample.md

lint:
	uv run ruff check . && uv run ruff format --check .

test:
	uv run pytest
