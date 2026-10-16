"""Tickets B2, B4 and B5 as revised by D020: audit how often one name sits on several ids.

Groups are names that map to several 11-digit ids and carry a corporate legal form (D022). A
sample is hand-labelled, split into dev and test with a fixed seed (D012), evaluated on dev, and
the test split is opened exactly once. Rules that propose "same entity" can be applied to the
entity table only if they meet the bar written in audit.toml before any label existed (D034)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path

import duckdb
from rapidfuzz.distance import Levenshtein

from appalti.stage import _connect

LEGAL_TOKENS = {
    "SRL", "SRLS", "SPA", "SNC", "SAS", "SAPA", "SCARL", "SCRL", "SOC", "SOCIETA",
    "COOP", "COOPERATIVA", "CONSORZIO", "FONDAZIONE", "ASSOCIAZIONE", "ONLUS",
    "GMBH", "LTD", "SARL", "SL",
}  # fmt: skip
LABELS = {"same", "different", "mixed", "unsure"}
RULES = ["typo", "succession", "homonym", "none"]
SAME_RULES = ["typo", "succession"]  # the rules that propose merging ids
FIELDS = [
    "group_id", "stratum", "stratum_size", "name", "n_ids", "ids", "awards_per_id",
    "years_per_id", "regions_per_id", "rule", "suggested", "label", "label_source",
]  # fmt: skip


class AuditError(Exception):
    """A labelling file is missing, incomplete or already used."""


def has_legal_form(name: str) -> bool:
    tokens = re.split(r"[^A-Z0-9]+", re.sub(r"[.']", "", name.upper()))
    return any(t in LEGAL_TOKENS for t in tokens)


@dataclass
class Group:
    name: str
    keys: list[str]
    stats: dict[str, dict]  # key -> {n, first, last, regions}

    @property
    def group_id(self) -> str:
        return "G" + hashlib.sha1(self.name.encode()).hexdigest()[:10]

    def ids(self) -> list[str]:
        return [k.split(":", 1)[1] for k in self.keys]


def classify(g: Group) -> tuple[str, str]:
    """Return (rule, suggested label) from the id-level evidence in the data."""
    ids = g.ids()
    # typo: the ids form one connected cluster in which neighbours differ by a single character
    seen, stack = {0}, [0]
    while stack:
        i = stack.pop()
        for j in range(len(ids)):
            if j not in seen and Levenshtein.distance(ids[i], ids[j]) == 1:
                seen.add(j)
                stack.append(j)
    if len(seen) == len(ids):
        return "typo", "same"
    spans = [(g.stats[k]["first"], g.stats[k]["last"]) for k in g.keys]
    if all(a is not None and b is not None for a, b in spans):
        ordered = sorted(spans)
        if all(ordered[i][1] < ordered[i + 1][0] for i in range(len(ordered) - 1)):
            return "succession", "same"
    regions = [set(g.stats[k]["regions"]) for k in g.keys]
    if all(regions) and all(
        regions[i].isdisjoint(regions[j])
        for i in range(len(regions))
        for j in range(i + 1, len(regions))
    ):
        return "homonym", "different"
    return "none", "unsure"


def load_groups(con: duckdb.DuckDBPyConnection) -> list[Group]:
    """Names with several 11-digit supplier ids and a legal form, with id-level evidence."""
    names = [
        r[0]
        for r in con.execute(
            "SELECT name FROM (SELECT DISTINCT name, key FROM party_key WHERE role = 'supplier'"
            " AND regexp_matches(key, '^IT-CF:[0-9]{11}$') AND name IS NOT NULL)"
            " GROUP BY name HAVING count(*) >= 2 ORDER BY name"
        ).fetchall()
        if has_legal_form(r[0])
    ]
    con.execute("CREATE OR REPLACE TEMP TABLE tmp_audit_names (name VARCHAR)")
    con.executemany("INSERT INTO tmp_audit_names VALUES (?)", [[n] for n in names])
    rows = con.execute(
        "SELECT k.name, k.key, count(*), min(a.award_year), max(a.award_year),"
        " list_distinct(list(a.region) FILTER (WHERE a.region <> 'unknown'))"
        " FROM party_key k JOIN tmp_audit_names n ON n.name = k.name"
        " JOIN clean_award_supplier cs ON cs.ocid = k.ocid AND cs.supplier_pid = k.pid"
        " JOIN fact_award a ON a.ocid = cs.ocid AND a.award_id = cs.award_id"
        " WHERE k.role = 'supplier' AND regexp_matches(k.key, '^IT-CF:[0-9]{11}$')"
        " GROUP BY k.name, k.key ORDER BY k.name, k.key"
    ).fetchall()
    # ids that never appear on an award (no linked fact row) still belong to the group
    keys = con.execute(
        "SELECT DISTINCT k.name, k.key FROM party_key k JOIN tmp_audit_names n ON n.name = k.name"
        " WHERE k.role = 'supplier' AND regexp_matches(k.key, '^IT-CF:[0-9]{11}$')"
        " ORDER BY k.name, k.key"
    ).fetchall()
    by_name: dict[str, Group] = {n: Group(n, [], {}) for n in names}
    for name, key in keys:
        by_name[name].keys.append(key)
        by_name[name].stats[key] = {"n": 0, "first": None, "last": None, "regions": []}
    for name, key, n, first, last, regions in rows:
        by_name[name].stats[key] = {
            "n": int(n), "first": first, "last": last, "regions": sorted(regions or []),
        }  # fmt: skip
    return [g for g in by_name.values() if len(g.keys) >= 2]


def build_alias_table(db: Path, rules: list[str]) -> int:
    """Fill entity_alias with the merges chosen by the audit: every id of a group on which a
    chosen rule fires maps to the smallest id of that group. Returns the number of ids merged."""
    bad = [r for r in rules if r not in SAME_RULES]
    if bad:
        raise AuditError(f"apply_rules may only name {SAME_RULES}, not {bad}")
    con = _connect(db)
    try:
        tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
        if not {"party_key", "fact_award"} <= tables:
            raise AuditError(
                "apply_rules is set but no earlier entity build exists; run it with"
                " apply_rules = [] first"
            )
        rows = []
        for g in load_groups(con):
            if classify(g)[0] in rules:
                target = min(g.keys)
                rows += [(k, target) for k in g.keys if k != target]
        con.execute("CREATE OR REPLACE TABLE entity_alias (key VARCHAR, merged_key VARCHAR)")
        con.executemany("INSERT INTO entity_alias VALUES (?, ?)", rows)
        return len(rows)
    finally:
        con.close()


def _fmt_group(g: Group, stratum: str, size: int) -> dict:
    rule, suggested = classify(g)
    st = g.stats
    return {
        "group_id": g.group_id,
        "stratum": stratum,
        "stratum_size": size,
        "name": g.name,
        "n_ids": len(g.keys),
        "ids": "; ".join(g.ids()),
        "awards_per_id": "; ".join(str(st[k]["n"]) for k in g.keys),
        "years_per_id": "; ".join(
            "-" if st[k]["first"] is None else f"{st[k]['first']}-{st[k]['last']}" for k in g.keys
        ),
        "regions_per_id": "; ".join("|".join(st[k]["regions"]) or "-" for k in g.keys),
        "rule": rule,
        "suggested": suggested,
        "label": "",
        "label_source": "",
    }


def sample(db: Path, cfg: dict, dev_path: Path, test_path: Path, force: bool = False) -> dict:
    for p in (dev_path, test_path):
        if p.exists() and not force:
            raise AuditError(f"{p} exists; refusing to overwrite labels (use --force to replace)")
    con = _connect(db)
    try:
        groups = load_groups(con)
    finally:
        con.close()
    by_rule: dict[str, list[Group]] = {r: [] for r in RULES}
    for g in groups:
        by_rule[classify(g)[0]].append(g)
    rng = random.Random(cfg["seed"])
    total, cap = int(cfg["sample_size"]), int(cfg["per_stratum_cap"])
    take = {r: min(len(gs), cap) for r, gs in by_rule.items()}
    spare = total - sum(take.values())
    while spare > 0:  # fill up from the strata that still have unsampled groups
        room = [r for r in RULES if take[r] < len(by_rule[r])]
        if not room:
            break
        for r in room:
            if spare > 0:
                take[r] += 1
                spare -= 1
    dev, test = [], []
    for rule in RULES:
        pool = sorted(by_rule[rule], key=lambda g: g.name)
        picked = rng.sample(pool, take[rule]) if pool else []
        n_dev = math.ceil(len(picked) * float(cfg["dev_share"]))
        dev += [_fmt_group(g, rule, len(pool)) for g in picked[:n_dev]]
        test += [_fmt_group(g, rule, len(pool)) for g in picked[n_dev:]]
    for path, rows in ((dev_path, dev), (test_path, test)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return {
        "groups": len(groups),
        "population": {r: len(by_rule[r]) for r in RULES},
        "dev": len(dev),
        "test": len(test),
    }


def read_labels(path: Path) -> list[dict]:
    if not path.exists():
        raise AuditError(f"{path} does not exist; run `appalti resolve sample` first")
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def accept_suggested(path: Path) -> int:
    """Fill blank labels with the suggested one and mark them, so the evidence can say so."""
    rows = read_labels(path)
    n = 0
    for r in rows:
        if not r["label"].strip():
            r["label"], r["label_source"] = r["suggested"], "suggested"
            n += 1
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return n


def _checked(rows: list[dict], path: Path) -> list[dict]:
    blank = [r["group_id"] for r in rows if not r["label"].strip()]
    if blank:
        raise AuditError(f"{path}: {len(blank)} of {len(rows)} groups have no label yet")
    bad = sorted({r["label"] for r in rows} - LABELS)
    if bad:
        raise AuditError(f"{path}: labels must be one of {sorted(LABELS)}, found {bad}")
    return rows


def _stats(rows: list[dict]) -> dict:
    strata: dict[str, dict] = {}
    for r in rows:
        s = strata.setdefault(r["stratum"], {"size": int(r["stratum_size"]), "n": 0, "c": {}})
        s["n"] += 1
        s["c"][r["label"]] = s["c"].get(r["label"], 0) + 1
    for s in strata.values():
        c = s["c"]
        s["decided"] = c.get("same", 0) + c.get("different", 0) + c.get("mixed", 0)
        s["split"] = c.get("same", 0) + c.get("mixed", 0)
    usable = {k: s for k, s in strata.items() if s["decided"] > 0}
    pop = sum(s["size"] for s in usable.values())
    p = sum(s["size"] / pop * s["split"] / s["decided"] for s in usable.values()) if pop else None
    var = sum(
        (s["size"] / pop) ** 2 * (s["split"] / s["decided"]) * (1 - s["split"] / s["decided"])
        / s["decided"] for s in usable.values()
    ) if pop else None  # fmt: skip
    ci = None if p is None else (max(0.0, p - 1.96 * var**0.5), min(1.0, p + 1.96 * var**0.5))
    rules = {}
    for rule in SAME_RULES:
        s = strata.get(rule)
        if s:
            rules[rule] = {
                "sampled": s["n"],
                "decided": s["decided"],
                "same": s["c"].get("same", 0),
                "precision": (s["c"].get("same", 0) / s["decided"]) if s["decided"] else None,
            }
    agree = sum(1 for r in rows if r["label"] == r["suggested"])
    return {
        "strata": strata, "split_rate": p, "ci": ci, "rules": rules,
        "agreement": agree / len(rows) if rows else None,
        "from_suggestions": sum(1 for r in rows if r["label_source"] == "suggested"),
        "from_claude": sum(1 for r in rows if r["label_source"] == "claude"),
        "rows": len(rows),
    }  # fmt: skip


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _report(title: str, st: dict, cfg: dict, split: str) -> list[str]:
    lines = [
        f"# {title}",
        "",
        (
            f"Split: **{split}**, {st['rows']} groups labelled; "
            f"{st['from_suggestions']} labels were taken from the suggested rule, "
            f"{st['from_claude']} were drafted by Claude from the sheet alone, "
            f"{st['rows'] - st['from_suggestions'] - st['from_claude']} entered by hand. "
            "Counts only: no name or id."
        ),
        "",
        (
            "A *split* is a group whose ids include one entity under more than one id (label "
            "`same` or `mixed`). Groups labelled `unsure` are left out of every rate."
        ),
        "",
        "| Stratum (rule) | Groups in population | Sampled | same | different | mixed | unsure |",
        "|---|---|---|---|---|---|---|",
    ]
    for rule in RULES:
        s = st["strata"].get(rule)
        if s:
            c = s["c"]
            lines.append(
                f"| {rule} | {s['size']:,} | {s['n']} | {c.get('same', 0)} | "
                f"{c.get('different', 0)} | {c.get('mixed', 0)} | {c.get('unsure', 0)} |"
            )
    ci = st["ci"]
    lines += [
        "",
        (
            f"**Estimated share of multi-id names where the id splits an entity: "
            f"{_pct(st['split_rate'])}** (95% interval "
            f"{_pct(ci[0]) if ci else 'n/a'} to {_pct(ci[1]) if ci else 'n/a'}, stratified)."
        ),
        f"Agreement between the suggested label and the final label: {_pct(st['agreement'])}.",
        "",
        "| Merge rule | Decided | Labelled same | Precision | Pre-registered bar |",
        "|---|---|---|---|---|",
    ]
    for rule, r in st["rules"].items():
        ok = (
            r["precision"] is not None
            and r["decided"] >= int(cfg["min_rule_support"])
            and r["precision"] >= float(cfg["min_rule_precision"])
        )
        lines.append(
            f"| {rule} | {r['decided']} | {r['same']} | {_pct(r['precision'])} | "
            f"{'met' if ok else 'not met'} (precision >= {cfg['min_rule_precision']}, "
            f"support >= {cfg['min_rule_support']}) |"
        )
    return lines + [""]


def evaluate(dev_path: Path, cfg: dict, out: Path) -> dict:
    rows = _checked(read_labels(dev_path), dev_path)
    st = _stats(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(_report("Entity audit, dev split (ticket B4)", st, cfg, "dev")) + "\n")
    return st


def confirm(test_path: Path, cfg: dict, audit_toml: Path, out_json: Path, out_md: Path) -> dict:
    """Open the test split once. A second call is refused."""
    if out_json.exists():
        raise AuditError(f"{out_json} exists: the test split has been opened already")
    rows = _checked(read_labels(test_path), test_path)
    st = _stats(rows)
    chosen = list(cfg.get("apply_rules", []))
    result = {
        "test_file_sha256": hashlib.sha256(test_path.read_bytes()).hexdigest(),
        "audit_toml_sha256": hashlib.sha256(audit_toml.read_bytes()).hexdigest(),
        "apply_rules": chosen,
        "split_rate": st["split_rate"],
        "ci": st["ci"],
        "rules": st["rules"],
        "chosen_rules_meet_bar": {
            r: bool(st["rules"].get(r) and st["rules"][r]["precision"] is not None
                    and st["rules"][r]["precision"] >= float(cfg["min_rule_precision"]))
            for r in chosen
        },
    }  # fmt: skip
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = _report("Entity audit, test confirmation (ticket B5)", st, cfg, "test")
    lines += [f"Rules chosen on dev (`apply_rules`): {chosen or 'none'}.", ""]
    out_md.write_text("\n".join(lines) + "\n")
    return result
