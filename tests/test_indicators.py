"""Indicators and Gate 2 on a synthetic world with known answers."""

import json
import shutil

import pytest

from appalti import gate2
from appalti import indicators as ind
from tests.test_entities import ROOT, build_db, q, rec, resolve

GATE_TOML = ROOT / "gate.toml"
PROC = ROOT / "labels" / "procedure_class.csv"
A1 = ("s1", "11111111111", "ALFA SRL")
A2 = ("s2", "22222222222", "ALFA SRL")  # same legal-form name, other id
B = ("s3", "33333333333", "BETA SRL")


def world() -> list[dict]:
    r, n = [], 0

    def add(count, year, **kw):
        nonlocal n
        for _ in range(count):
            r.append(rec(n, kw.pop("sup", None) or [A1], year=year, **kw))
            n += 1

    add(10, 2019, cpv="45", amount=100.0, tender_amount=100.0)
    add(12, 2020, cpv="45", amount=100.0, tender_amount=100.0)
    add(40, 2021, cpv="45", amount=100.0, tender_amount=100.0)
    add(40, 2022, cpv="33", amount=100.0, tender_amount=100.0, tenderers=1)
    return r


@pytest.fixture
def built(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, world())
    resolve(tmp_path, manifest, db)
    return tmp_path, manifest, db


def run_ind(tmp, manifest, db):
    return ind.run("t.jsonl", manifest, db, GATE_TOML, PROC, tmp / "i.md")


def test_values_and_counts(built):
    tmp, manifest, db = built
    res = run_ind(tmp, manifest, db)
    assert res.rows > 0
    v = {
        (r[0], r[1]): r[2]
        for r in q(
            db,
            "SELECT clock, period, value FROM indicator_value WHERE indicator = 'awarded_value'"
            " AND slice_type = 'all' AND variant = 'headline'",
        )
    }
    assert v[("award_year", 2019)] == 1000.0 and v[("award_year", 2021)] == 4000.0
    n = q(
        db,
        "SELECT n FROM indicator_value WHERE indicator='awarded_value' AND period=2020 "
        "AND clock='award_year' AND slice_type='all' AND variant='headline'",
    )
    assert n == [(12,)]


def test_single_bidder_denominator_is_published_counts_only(built):
    tmp, manifest, db = built
    run_ind(tmp, manifest, db)
    rows = {
        (r[0], r[1]): (r[2], r[3])
        for r in q(
            db,
            "SELECT clock, period, value, n FROM indicator_value WHERE indicator = 'single_bidder'",
        )
    }
    assert rows[("award_year", 2021)] == (None, 0)  # nothing published: no value, not 0%
    assert rows[("award_year", 2022)] == (1.0, 40)


def test_concentration_range_and_split_by_name(tmp_path, monkeypatch):
    recs = []
    for i in range(3):
        recs.append(rec(i, [A1], amount=300.0, tender_amount=300.0))
    for i in range(3, 6):
        recs.append(rec(i, [A2], amount=300.0, tender_amount=300.0))
    for i in range(6, 8):
        recs.append(rec(i, [B], amount=100.0, tender_amount=100.0))
    manifest, db = build_db(tmp_path, monkeypatch, recs)
    resolve(tmp_path, manifest, db)
    run_ind(tmp_path, manifest, db)
    rows = {
        r[0]: r[1]
        for r in q(
            db,
            "SELECT variant, value FROM indicator_value WHERE indicator='concentration'"
            " AND clock='award_year'",
        )
    }
    # only three suppliers exist, so the top five hold everything on both readings
    assert rows["point"] == pytest.approx(1.0) and rows["merged_upper"] == pytest.approx(1.0)
    assert q(db, "SELECT count(*) FROM ind_name_group")[0][0] == 2  # both ALFA ids


def test_both_clocks_use_their_own_year(tmp_path, monkeypatch):
    recs = [rec(0, [A1], year=2021, tender_year=2020), rec(1, [A1], year=2021)]
    manifest, db = build_db(tmp_path, monkeypatch, recs)
    resolve(tmp_path, manifest, db)
    run_ind(tmp_path, manifest, db)
    got = q(
        db,
        "SELECT clock, period, n FROM indicator_value WHERE indicator='awarded_value'"
        " AND slice_type='all' AND variant='headline' ORDER BY 1, 2",
    )
    assert got == [("award_year", 2021, 2), ("tender_year", 2020, 1), ("tender_year", 2021, 1)]


def test_indicators_refuse_without_fact_tables(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, world())
    with pytest.raises(ind.IndicatorsRefused):
        run_ind(tmp_path, manifest, db)


def test_gate2_refuses_with_reasons(built):
    tmp, manifest, db = built
    run_ind(tmp, manifest, db)
    res = gate2.check(db, GATE_TOML, tmp / "g2.md")
    assert res.decisions > 0 and res.refusals > 0 and res.passed > 0
    con = __import__("duckdb").connect(str(db), read_only=True)
    decs = gate2.decisions(con)
    con.close()

    def find(indicator, clock, periods):
        return next(
            d
            for d in decs
            if (d["indicator"], d["clock"], d["periods"]) == (indicator, clock, periods)
        )

    ok = find("awarded_value", "award_year", ["2019", "2020"])
    assert ok["passed"]
    vol = find("awarded_value", "award_year", ["2020", "2021"])
    assert not vol["passed"] and vol["reasons"]["failed"][0]["measure"] == "volume_ratio"
    drift = find("awarded_value", "award_year", ["2021", "2022"])
    assert any(f["measure"] == "composition_drift" for f in drift["reasons"]["failed"])
    sb = find("single_bidder", "award_year", ["2019"])
    assert not sb["passed"] and sb["reasons"]["failed"][0]["measure"] == "populatedness"
    # 2022 has tenderer counts, but its only neighbour was refused: isolated (D040)
    iso = find("single_bidder", "award_year", ["2022"])
    assert not iso["passed"] and iso["reasons"]["failed"][0]["measure"] == "isolated"
    assert find("awarded_value", "award_year", ["2020"])["passed"]  # has a comparable neighbour
    assert not find("awarded_value", "award_year", ["2021"])["passed"]  # both pairs refused
    text = gate2.refusal_text("awarded_value", "award_year", vol["periods"], vol["reasons"])
    assert text.startswith("Awarded value, 2020 compared with 2021 (award year): not published.")
    assert "3.33 of the 2020 count, outside the accepted band of 0.5 to 2.0" in text
    assert "not comparable on this measure" in text
    assert "None: every comparison passed" not in (tmp / "g2.md").read_text()


def test_gate2_is_recorded_not_only_acted_on(built):
    tmp, manifest, db = built
    run_ind(tmp, manifest, db)
    gate2.check(db, GATE_TOML, tmp / "g2.md")
    gate2.check(db, GATE_TOML, tmp / "g2.md")
    n, runs = q(db, "SELECT count(*), count(DISTINCT run_id) FROM gate_decision")[0]
    assert runs == 2 and n % 2 == 0  # append-only: both runs kept
    ids = [r[0] for r in q(db, "SELECT decision_id FROM gate_decision ORDER BY 1")]
    assert ids == list(range(1, n + 1))


def test_no_names_or_ids_in_evidence(built):
    tmp, manifest, db = built
    run_ind(tmp, manifest, db)
    gate2.check(db, GATE_TOML, tmp / "g2.md")
    text = (tmp / "i.md").read_text() + (tmp / "g2.md").read_text()
    assert "ALFA" not in text and "11111111111" not in text and "BETA" not in text
    assert json.dumps(world()[0]) is not None and shutil is not None


def test_procedure_mapping_is_complete_and_unambiguous():
    import csv

    rows = list(csv.DictReader(PROC.open()))
    codes = [int(r["code"]) for r in rows]
    assert len(codes) == len(set(codes))  # one class per code
    from_recon = {
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        12,
        14,
        15,
        16,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        40,
        114,
    }  # every code seen in recon5
    assert from_recon <= set(codes)


def test_a_single_year_with_no_neighbour_is_judged_on_its_own_data(tmp_path, monkeypatch):
    recs = [rec(i, [A1], year=2021, cpv="45") for i in range(5)]
    manifest, db = build_db(tmp_path, monkeypatch, recs)
    resolve(tmp_path, manifest, db)
    run_ind(tmp_path, manifest, db)
    gate2.check(db, GATE_TOML, tmp_path / "g2.md")
    rows = q(
        db,
        "SELECT indicator, passed FROM gate_decision WHERE clock = 'award_year'"
        " AND len(periods) = 1 ORDER BY 1",
    )
    assert dict(rows)["awarded_value"] is True  # nothing to compare with: nothing to refuse
    assert dict(rows)["single_bidder"] is False  # field empty


def test_populatedness_failure_is_one_sentence_for_a_pair(built):
    tmp, manifest, db = built
    run_ind(tmp, manifest, db)
    gate2.check(db, GATE_TOML, tmp / "g2.md")
    txt = q(
        db,
        "SELECT reasons FROM gate_decision WHERE indicator = 'single_bidder'"
        " AND clock = 'award_year' AND periods = ['2019', '2020']",
    )[0][0]
    failed = json.loads(txt)["failed"]
    assert sum(1 for f in failed if f["measure"] == "populatedness") == 1
    assert "0.0% of 2019 records and 0.0% of 2020 records" in failed[0]["text"]
