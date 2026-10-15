"""Command line entry point: `appalti <command>`: `download` (A2) and `stage` (A3)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from appalti import download as dl
from appalti import stage as st


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="appalti")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("download", help="fetch a bulk file and record its sha256 in the manifest")
    group = d.add_mutually_exclusive_group()
    group.add_argument("--year", type=int, help="fetch <year>.jsonl.gz instead of the full file")
    group.add_argument("--file", help="exact file name on the registry, e.g. full.jsonl.gz")
    d.add_argument("--verify", action="store_true", help="only recheck pinned hashes, no download")
    d.add_argument("--raw-dir", default="data/raw", type=Path)
    d.add_argument("--manifest", default="manifest.json", type=Path)

    g = sub.add_parser("stage", help="load a pinned raw file into typed stg_* tables and reconcile")
    g.add_argument("--file", default="full.jsonl.gz", help="file name inside --raw-dir")
    g.add_argument("--raw-dir", default="data/raw", type=Path)
    g.add_argument("--manifest", default="manifest.json", type=Path)
    g.add_argument("--db", default="data/appalti.duckdb", type=Path)
    g.add_argument("--expected", default="expected_counts.toml", type=Path)
    g.add_argument("--out", default="evidence/stage_reconciliation.md", type=Path)

    args = parser.parse_args(argv)

    if args.command == "stage":
        try:
            checks = st.run(
                args.raw_dir / args.file, args.manifest, args.db, args.expected, args.out
            )
        except st.NotPinned as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        for c in checks:
            print(
                f"{c.status:8} {c.name}: staged {c.actual:,}"
                + (f", stated {c.expected:,}" if c.expected is not None else "")
            )
        bad = [c for c in checks if c.status == "MISMATCH"]
        print(f"wrote {args.out}; {len(bad)} mismatch(es)")
        return 1 if bad else 0

    if args.verify:
        problems = dl.verify(args.raw_dir, args.manifest)
        for p in problems:
            print(f"PROBLEM  {p}")
        print("manifest verified" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    name = dl.file_name_for(args.year, args.file)
    try:
        result = dl.download(name, args.raw_dir, args.manifest)
    except dl.ChecksumMismatch as exc:
        print(f"REFUSED  {exc}", file=sys.stderr)
        return 2
    print(f"{result}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
