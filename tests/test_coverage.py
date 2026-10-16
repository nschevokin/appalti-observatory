"""Coverage tests on a small synthetic file with known counts."""

import duckdb
import pytest

from appalti import coverage as cv
from appalti import validate as va
from appalti.cli import main
from tests.test_validate import GATE, build, good

GATE2 = GATE.parent / "gate.toml"


def records() -> list[dict]:
    out = []
    for i in range(100):
        d = good(i)
        year = 2021 if i < 60 else 2022
        d["date"] = f"{year}-03-01T10:00:00Z"
        d["tender"]["tenderPeriod"] = {"startDate": f"{year}-01-01"}
        d["tender"]["procurementMethodDetails"] = "COD:1 ; TITLE:x"
        d["awards"][0]["date"] = f"{year}-02-01"
        if i < 30:
            d["tender"]["numberOfTenderers"] = 2
        if i >= 90:  # ten processes without a contract
            d["contracts"] = []
        out.append(d)
    return out


def counts(db, run_id, clock, period, field):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(
            "SELECT n_total, n_populated FROM coverage"
            " WHERE run_id = ? AND clock = ? AND period = ? AND field = ?",
            [run_id, clock, period, field],
        ).fetchone()
    finally:
        con.close()


@pytest.fixture
def ready(tmp_path, monkeypatch):
    manifest, db = build(tmp_path, monkeypatch, records())
    va.run("t.jsonl", manifest, db, GATE, tmp_path / "none.toml", tmp_path / "g.md")
    return tmp_path, manifest, db


def test_counts_per_period_and_field(ready):
    tmp, manifest, db = ready
    res = cv.run("t.jsonl", manifest, db, GATE2, tmp / "c.md")
    assert counts(db, res.run_id, "tender_start_year", "2021", "records") == (60, 60)
    assert counts(db, res.run_id, "tender_start_year", "2022", "records") == (40, 40)
    assert counts(db, res.run_id, "tender_start_year", "2021", "number_of_tenderers") == (60, 30)
    assert counts(db, res.run_id, "tender_start_year", "2022", "number_of_tenderers") == (40, 0)
    assert counts(db, res.run_id, "award_year", "2022", "has_contract") == (40, 30)
    assert counts(db, res.run_id, "release_year", "2021", "buyer_postal_code") == (60, 0)
    report = (tmp / "c.md").read_text()
    assert "| 2021 | 60 |" in report and "| 2022 | 40 | 0.67 |" in report


def test_volume_ratio_outside_band_is_marked(tmp_path, monkeypatch):
    recs = records()
    for i, d in enumerate(recs):
        if i >= 20:
            year = 2022
            d["date"] = f"{year}-03-01T10:00:00Z"
            d["tender"]["tenderPeriod"] = {"startDate": f"{year}-01-01"}
            d["awards"][0]["date"] = f"{year}-02-01"
    manifest, db = build(tmp_path, monkeypatch, recs)
    va.run("t.jsonl", manifest, db, GATE, tmp_path / "none.toml", tmp_path / "g.md")
    cv.run("t.jsonl", manifest, db, GATE2, tmp_path / "c.md")
    assert "4.00 **outside**" in (tmp_path / "c.md").read_text()  # 80 / 20


def test_runs_are_appended_never_replaced(ready):
    tmp, manifest, db = ready
    first = cv.run("t.jsonl", manifest, db, GATE2, tmp / "c.md")
    second = cv.run("t.jsonl", manifest, db, GATE2, tmp / "c.md")
    assert first.run_id != second.run_id
    hist = cv.history(db)
    assert sum(n for _, n in hist) == first.rows + second.rows


def test_refused_when_gate1_aborted(tmp_path, monkeypatch, capsys):
    recs = records()
    for i in (1, 2, 3):
        recs[i]["awards"][0]["value"]["amount"] = -1
    manifest, db = build(tmp_path, monkeypatch, recs)
    assert va.run("t.jsonl", manifest, db, GATE, tmp_path / "none.toml", tmp_path / "g.md").aborted
    with pytest.raises(cv.CoverageRefused):
        cv.run("t.jsonl", manifest, db, GATE2, tmp_path / "c.md")
    args = ["coverage", "--file", "t.jsonl", "--manifest", str(manifest), "--db", str(db)]
    assert main([*args, "--gate", str(GATE2), "--out", "x.md"]) == 2
