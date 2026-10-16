RAW ?= data/raw/full.jsonl.gz
URL := https://data.open-contracting.org/en/publication/117/download?name=full.jsonl.gz

.PHONY: fetch-full stage validate recon recon2 recon3 recon4 recon-sample lint test

# Ticket A2: download (or adopt an existing file) and pin its sha256 in manifest.json.
fetch-full:
	uv run appalti download

# Ticket A3: typed staging tables plus row-count reconciliation (writes evidence/).
stage:
	uv run appalti stage

# Ticket A4: Gate 1, writes rejected_record and evidence/gate1_rejects.md.
validate:
	uv run appalti validate

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

# Smoke test of the queries on a tiny synthetic file
recon-sample:
	uv run python scripts/run_recon.py --raw tests/fixtures/ocds_sample.jsonl --out /tmp/recon_sample.md

lint:
	uv run ruff check . && uv run ruff format --check .

test:
	uv run pytest
