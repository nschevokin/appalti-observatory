RAW ?= data/raw/full.jsonl.gz
URL := https://data.opencontracting.org/en/publication/117/download?name=full.jsonl.gz

.PHONY: fetch-full recon recon-sample lint test

# Day-1 manual download. The proper `appalti download` + manifest is ticket A2.
fetch-full:
	mkdir -p data/raw
	curl -L --fail -o $(RAW) "$(URL)"
	sha256sum $(RAW)
	@echo "Record the sha256 and today's date in docs/recon.md"

recon:
	uv run python scripts/run_recon.py --raw $(RAW) --out docs/recon_output.md

# Smoke test of the queries on a tiny synthetic file
recon-sample:
	uv run python scripts/run_recon.py --raw tests/fixtures/ocds_sample.jsonl --out /tmp/recon_sample.md

lint:
	uv run ruff check . && uv run ruff format --check .

test:
	uv run pytest
