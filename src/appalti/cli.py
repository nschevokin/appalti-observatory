"""Command line entry point: `appalti <command>`: `download` (A2), `stage` (A3), `validate` (A4), `coverage` (A5), `resolve` and `regions` (week 2)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from appalti import audit as au
from appalti import coverage as cv
from appalti import download as dl
from appalti import entities as en
from appalti import gate2 as g2
from appalti import indicators as ind
from appalti import regions as rg
from appalti import site as sitemod
from appalti import stage as st
from appalti import status as statusmod
from appalti import validate as va


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

    v = sub.add_parser("validate", help="Gate 1: validate staged records, write rejected_record")
    v.add_argument("--file", default="full.jsonl.gz")
    v.add_argument("--manifest", default="manifest.json", type=Path)
    v.add_argument("--db", default="data/appalti.duckdb", type=Path)
    v.add_argument("--gate", default="gate1.toml", type=Path)
    v.add_argument("--expected", default="expected_counts.toml", type=Path)
    v.add_argument("--out", default="evidence/gate1_rejects.md", type=Path)

    c = sub.add_parser("coverage", help="records per period and populatedness per field")
    c.add_argument("--file", default="full.jsonl.gz")
    c.add_argument("--manifest", default="manifest.json", type=Path)
    c.add_argument("--db", default="data/appalti.duckdb", type=Path)
    c.add_argument("--gate", default="gate.toml", type=Path)
    c.add_argument("--out", default="evidence/coverage.md", type=Path)

    r = sub.add_parser("resolve", help="entities, award facts, and the entity audit")
    rs = r.add_subparsers(dest="action", required=True)
    for name in ("build", "sample", "accept-suggested", "eval", "confirm"):
        a = rs.add_parser(name)
        a.add_argument("--db", default="data/appalti.duckdb", type=Path)
        a.add_argument("--audit", default="audit.toml", type=Path)
        a.add_argument("--dev", default="audit/groups_dev.csv", type=Path)
        a.add_argument("--test", default="audit/groups_test.csv", type=Path)
    rs.choices["build"].add_argument("--file", default="full.jsonl.gz")
    rs.choices["build"].add_argument("--manifest", default="manifest.json", type=Path)
    rs.choices["build"].add_argument("--gate", default="gate1.toml", type=Path)
    rs.choices["build"].add_argument("--cap", default="labels/cap_region.csv", type=Path)
    rs.choices["build"].add_argument("--out", default="evidence/entities.md", type=Path)
    rs.choices["sample"].add_argument("--force", action="store_true")
    rs.choices["accept-suggested"].add_argument("--split", choices=["dev", "test"], required=True)

    g = sub.add_parser("regions", help="check the postal-code to region mapping (D026)")
    gs = g.add_subparsers(dest="action", required=True)
    for name in ("sample", "eval"):
        a = gs.add_parser(name)
        a.add_argument("--sheet", default="audit/region_check.csv", type=Path)
    gs.choices["sample"].add_argument("--db", default="data/appalti.duckdb", type=Path)
    gs.choices["eval"].add_argument("--out", default="evidence/region_check.md", type=Path)

    i = sub.add_parser("indicators", help="compute the four indicators on both clocks (C1)")
    i.add_argument("--file", default="full.jsonl.gz")
    i.add_argument("--manifest", default="manifest.json", type=Path)
    i.add_argument("--db", default="data/appalti.duckdb", type=Path)
    i.add_argument("--gate", default="gate.toml", type=Path)
    i.add_argument("--proc", default="labels/procedure_class.csv", type=Path)
    i.add_argument("--out", default="evidence/indicators.md", type=Path)

    gg = sub.add_parser("gate", help="Gate 2: comparability (C2)")
    gs2 = gg.add_subparsers(dest="action", required=True)
    gc = gs2.add_parser("check")
    gc.add_argument("--db", default="data/appalti.duckdb", type=Path)
    gc.add_argument("--gate", default="gate.toml", type=Path)
    gc.add_argument("--out", default="evidence/gate2.md", type=Path)

    sg = sub.add_parser("site", help="render the static site (C3)")
    ss = sg.add_subparsers(dest="action", required=True)
    sb = ss.add_parser("build")
    sb.add_argument("--db", default="data/appalti.duckdb", type=Path)
    sb.add_argument("--out", default="site", type=Path)
    sb.add_argument("--evidence", default="evidence", type=Path)

    stt = sub.add_parser("status", help="current run, counts, last Gate 2 decisions")
    stt.add_argument("--db", default="data/appalti.duckdb", type=Path)

    args = parser.parse_args(argv)

    if args.command == "status":
        print("\n".join(statusmod.lines(args.db)))
        return 0

    if args.command == "indicators":
        try:
            res = ind.run(args.file, args.manifest, args.db, args.gate, args.proc, args.out)
        except ind.IndicatorsRefused as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        print(f"run {res.run_id}: {res.rows:,} indicator rows; wrote {args.out}")
        return 0

    if args.command == "gate":
        try:
            r2 = g2.check(args.db, args.gate, args.out)
        except ind.IndicatorsRefused as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        print(f"run {r2.run_id}: {r2.decisions} decisions, {r2.refusals} refused; wrote {args.out}")
        return 0

    if args.command == "site":
        try:
            pages = sitemod.build(args.db, args.out, args.evidence)
        except sitemod.SiteRefused as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        print(f"wrote {len(pages)} pages to {args.out}")
        return 0

    if args.command == "regions":
        try:
            if args.action == "sample":
                n = rg.sample(args.db, args.sheet)
                print(
                    f"wrote {args.sheet} with {n} rows; fill the status column with ok or wrong:<Region>"
                )
            else:
                res = rg.evaluate(args.sheet, args.out)
                print(f"{res['wrong']} wrong of {res['n']}; wrote {args.out}")
        except rg.RegionCheckError as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        return 0

    if args.command == "resolve":
        try:
            cfg = en.load_audit(args.audit)
            if args.action == "build":
                res = en.run(
                    args.file, args.manifest, args.db, args.gate, args.audit, args.cap, args.out
                )
                for name, want, got in res.checks:
                    print(f"{'ok' if want == got else 'FAIL':5}{name}: {got:,}")
                print(f"run {res.run_id}; wrote {args.out}")
                return 1 if res.failed else 0
            if args.action == "sample":
                info = au.sample(args.db, cfg, args.dev, args.test, args.force)
                print(
                    f"{info['groups']:,} multi-id legal-form names; population {info['population']}"
                )
                print(
                    f"wrote {args.dev} ({info['dev']} groups) and {args.test} ({info['test']} groups)"
                )
                return 0
            if args.action == "accept-suggested":
                path = args.dev if args.split == "dev" else args.test
                print(f"{au.accept_suggested(path)} blank labels filled from the suggested rule")
                return 0
            if args.action == "eval":
                stats = au.evaluate(args.dev, cfg, Path("evidence/audit_dev.md"))
                print(
                    f"split rate {stats['split_rate']}; rules {stats['rules']}; wrote evidence/audit_dev.md"
                )
                return 0
            res = au.confirm(
                args.test,
                cfg,
                args.audit,
                Path("evidence/audit_test_confirmation.json"),
                Path("evidence/audit_test.md"),
            )
            print(f"test opened once; chosen rules meet the bar: {res['chosen_rules_meet_bar']}")
            return 0
        except (au.AuditError, en.EntitiesRefused) as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2

    if args.command == "coverage":
        try:
            res = cv.run(args.file, args.manifest, args.db, args.gate, args.out)
        except cv.CoverageRefused as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        print(f"run {res.run_id}: {res.rows:,} coverage rows stored; wrote {args.out}")
        return 0

    if args.command == "validate":
        try:
            res = va.run(args.file, args.manifest, args.db, args.gate, args.expected, args.out)
        except va.StageMismatch as exc:
            print(f"REFUSED  {exc}", file=sys.stderr)
            return 2
        for name, n, procs in res.by_reason:
            print(f"{name:22} {n:>9,} rows  {procs:>9,} processes")
        print(f"rejected {res.rejected_processes:,} of {res.lines:,} ({res.share:.4%})")
        for m in res.expectation_mismatches:
            print(f"DIFFERS  {m}")
        if res.aborted:
            print(f"ABORT  more than {res.max_share:.0%} rejected; no clean_* views created")
            return 3
        print(f"wrote {args.out}")
        return 1 if res.expectation_mismatches else 0

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
