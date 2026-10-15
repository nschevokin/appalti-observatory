"""Run sql/recon/recon.sql against a JSONL(.gz) file and write every query plus its
result, with the run date, to a markdown file. Measurement only, not pipeline code."""

import argparse
import datetime as dt
import re
from pathlib import Path

import duckdb

BLOCK = re.compile(r"^-- @(setup|query) (\w+)\s*$", re.M)


def split_blocks(text: str):
    marks = list(BLOCK.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        yield m.group(1), m.group(2), text[m.end():end].strip()


def md_table(cols, rows) -> str:
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--sql", default="sql/recon/recon.sql")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    con = duckdb.connect()
    text = Path(args.sql).read_text().replace("$RAW_FILE", args.raw)
    report = [
        "# Recon output",
        f"Run date: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Input: `{args.raw}`",
        f"DuckDB: {duckdb.__version__}",
        "",
    ]
    for kind, name, sql in split_blocks(text):
        if kind == "setup":
            con.execute(sql)
            continue
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        report += [f"## {name}", "```sql", sql, "```", md_table(cols, rows), ""]
        print(f"ok  {name}  ({len(rows)} rows)")
    Path(args.out).write_text("\n".join(report))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
