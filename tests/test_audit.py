"""Audit tests: group rules, fixed-seed sampling, labels, one-time test confirmation, merging."""

import csv
import json

import pytest

from appalti import audit as au
from appalti import regions as rg
from appalti.entities import load_audit
from tests.test_entities import AUDIT, build_db, q, rec, resolve

LOMBARDY, LAZIO = "20100", "00100"


def pair(base: int, kind: str) -> list[tuple[str, int, str]]:
    """Two ids for one name, with the evidence that makes one rule fire: (id, year, postal)."""
    a, b = f"{base:011d}", f"{base + 5_500_000:011d}"
    if kind == "typo":
        b = f"{base + 1:011d}"
        return [(a, 2021, LOMBARDY), (b, 2021, LOMBARDY)]
    if kind == "succession":
        return [(a, 2019, LOMBARDY), (b, 2022, LOMBARDY)]
    if kind == "homonym":
        return [(a, 2021, LOMBARDY), (b, 2021, LAZIO)]
    return [(a, 2021, LOMBARDY), (b, 2021, LOMBARDY)]  # none


def records() -> list[dict]:
    out, n = [], 0
    for kind in ("typo", "succession", "homonym", "none"):
        for g in range(5):
            name = f"{kind.upper()}{g} SRL"
            for ident, year, postal in pair(10_000_000 * (g + 1) + 100_000_000 * len(out), kind):
                for _ in range(2):
                    out.append(rec(n, [(f"p{n}", ident, name)], year=year, postal=postal))
                    n += 1
    out.append(rec(n, [("x1", "70000000001", "ROSSI MARIO")], year=2021))
    out.append(rec(n + 1, [("x2", "70000000002", "ROSSI MARIO")], year=2021))  # no legal form
    return out


@pytest.fixture
def ready(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, records())
    resolve(tmp_path, manifest, db)
    return tmp_path, manifest, db


def cfg() -> dict:
    return load_audit(AUDIT)


def test_rules_and_population(ready):
    tmp, _, db = ready
    info = au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    assert info["population"] == {"typo": 5, "succession": 5, "homonym": 5, "none": 5}
    assert info["dev"] + info["test"] == 20  # the group without a legal form is left out
    rows = au.read_labels(tmp / "dev.csv") + au.read_labels(tmp / "test.csv")
    for r in rows:
        assert r["rule"] == r["stratum"] and r["name"].startswith(r["rule"].upper())
    assert not any("ROSSI" in r["name"] for r in rows)


def test_sampling_is_reproducible_and_never_overwrites(ready):
    tmp, _, db = ready
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    first = (tmp / "dev.csv").read_text(), (tmp / "test.csv").read_text()
    with pytest.raises(au.AuditError):
        au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv", force=True)
    assert ((tmp / "dev.csv").read_text(), (tmp / "test.csv").read_text()) == first
    dev = {r["group_id"] for r in au.read_labels(tmp / "dev.csv")}
    test = {r["group_id"] for r in au.read_labels(tmp / "test.csv")}
    assert dev.isdisjoint(test)


def test_eval_refuses_blank_labels_then_computes_the_weighted_rate(ready):
    tmp, _, db = ready
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    with pytest.raises(au.AuditError):
        au.evaluate(tmp / "dev.csv", cfg(), tmp / "dev.md")
    assert au.accept_suggested(tmp / "dev.csv") == 12  # 3 dev groups in each of 4 strata
    st = au.evaluate(tmp / "dev.csv", cfg(), tmp / "dev.md")
    # typo and succession all 'same', homonym all 'different', none all 'unsure' (left out)
    assert st["split_rate"] == pytest.approx(10 / 15)
    assert st["from_suggestions"] == 12
    text = (tmp / "dev.md").read_text()
    assert "not met" in text  # 3 decided groups is below the pre-registered support of 10
    assert "ROSSI" not in text and "TYPO0" not in text  # counts only


def test_bad_label_is_refused(ready):
    tmp, _, db = ready
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    au.accept_suggested(tmp / "dev.csv")
    rows = au.read_labels(tmp / "dev.csv")
    rows[0]["label"] = "maybe"
    with (tmp / "dev.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=au.FIELDS)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(au.AuditError):
        au.evaluate(tmp / "dev.csv", cfg(), tmp / "dev.md")


def test_test_split_opens_once(ready):
    tmp, _, db = ready
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    au.accept_suggested(tmp / "test.csv")
    out = tmp / "confirm.json"
    res = au.confirm(tmp / "test.csv", cfg(), AUDIT, out, tmp / "confirm.md")
    assert json.loads(out.read_text())["test_file_sha256"] == res["test_file_sha256"]
    with pytest.raises(au.AuditError):
        au.confirm(tmp / "test.csv", cfg(), AUDIT, out, tmp / "confirm.md")


def test_applied_rule_merges_entities(ready, tmp_path):
    tmp, manifest, db = ready
    before = q(db, "SELECT count(*) FROM entity")[0][0]
    audit2 = tmp / "audit2.toml"
    audit2.write_text(AUDIT.read_text().replace("apply_rules = []", 'apply_rules = ["typo"]'))
    resolve(tmp, manifest, db, audit2)
    after = q(db, "SELECT count(*) FROM entity")[0][0]
    assert before - after == 5  # five typo groups, one merged id each
    merged = q(db, "SELECT count(*) FROM entity WHERE method = 'name_match'")[0][0]
    assert merged == 5
    # the pre-merge key stays on party_key, so the audit can always be rerun
    assert q(db, "SELECT count(DISTINCT key) FROM party_key WHERE role = 'supplier'")[0][0] > after


def test_region_sheet(ready):
    tmp, _, db = ready
    n = rg.sample(db, tmp / "regions.csv", n=2)
    assert n == 2
    rows = list(csv.DictReader((tmp / "regions.csv").open()))
    assert {r["postal_code"] for r in rows} <= {LOMBARDY, LAZIO}
    assert all(r["locality"] == "TESTVILLE" for r in rows)
    with pytest.raises(rg.RegionCheckError):
        rg.evaluate(tmp / "regions.csv", tmp / "r.md")
    rows[0]["status"], rows[1]["status"] = "ok", "wrong:Veneto"
    with (tmp / "regions.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rg.FIELDS)
        w.writeheader()
        w.writerows(rows)
    res = rg.evaluate(tmp / "regions.csv", tmp / "r.md")
    assert res == {"n": 2, "wrong": 1, "accuracy": 0.5}


def test_report_discloses_claude_drafted_labels(ready):
    tmp, _, db = ready
    au.sample(db, cfg(), tmp / "dev.csv", tmp / "test.csv")
    au.accept_suggested(tmp / "dev.csv")
    rows = au.read_labels(tmp / "dev.csv")
    for r in rows[:4]:
        r["label_source"] = "claude"
    with (tmp / "dev.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=au.FIELDS)
        w.writeheader()
        w.writerows(rows)
    au.evaluate(tmp / "dev.csv", cfg(), tmp / "dev.md")
    assert "4 were drafted by Claude" in (tmp / "dev.md").read_text()
