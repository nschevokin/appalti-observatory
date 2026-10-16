"""Gate 1 tests: each rule rejects a deliberately corrupted record with the right reason code,
and the 2 percent abort rule fires."""

import copy
import json
from pathlib import Path

import duckdb
import pytest

from appalti import download as dl
from appalti import stage as st
from appalti import validate as va
from appalti.cli import main

GATE = Path(__file__).resolve().parents[1] / "gate1.toml"


def good(i: int) -> dict:
    return {
        "ocid": f"o{i}",
        "id": f"r{i}",
        "tag": ["award"],
        "initiationType": "tender",
        "date": "2021-03-01T10:00:00Z",
        "tender": {"value": {"amount": 1000, "currency": "EUR"}},
        "buyer": {"id": "p1"},
        "parties": [
            {"id": "p1", "roles": ["buyer"], "name": "COMUNE", "identifier": {"id": "1"}},
            {"id": "p2", "roles": ["supplier"], "name": "ACME SRL", "identifier": {"id": "2"}},
        ],
        "awards": [
            {
                "id": "a1",
                "date": "2021-03-02",
                "value": {"amount": 900, "currency": "EUR"},
                "suppliers": [{"id": "p2"}],
            }
        ],
        "contracts": [{"id": "c1", "awardID": "a1"}],
    }


def corrupt_missing_tag(d):
    del d["tag"]


def corrupt_missing_ocid(d):
    del d["ocid"]


def corrupt_old_date(d):
    d["date"] = "2018-12-31T00:00:00Z"


def corrupt_unparseable_date(d):
    d["date"] = "not a date"


def corrupt_negative(d):
    d["awards"][0]["value"]["amount"] = -5


def corrupt_text_amount(d):
    d["awards"][0]["value"]["amount"] = "abc"


def corrupt_currency(d):
    d["awards"][0]["value"]["currency"] = "USD"


def corrupt_no_currency(d):
    del d["awards"][0]["value"]["currency"]


def corrupt_award_ref(d):
    d["contracts"][0]["awardID"] = "zzz"


def corrupt_supplier_ref(d):
    d["awards"][0]["suppliers"] = [{"id": "ghost"}]


def corrupt_buyer_ref(d):
    d["buyer"]["id"] = "ghost"


CASES = [
    (corrupt_missing_tag, "missing_required"),
    (corrupt_missing_ocid, "missing_required"),
    (corrupt_old_date, "date_out_of_range"),
    (corrupt_unparseable_date, "date_out_of_range"),
    (corrupt_negative, "bad_amount"),
    (corrupt_text_amount, "bad_amount"),
    (corrupt_currency, "unexpected_currency"),
    (corrupt_no_currency, "unexpected_currency"),
    (corrupt_award_ref, "dangling_award_ref"),
    (corrupt_supplier_ref, "dangling_party_ref"),
    (corrupt_buyer_ref, "dangling_party_ref"),
]


def build(tmp: Path, monkeypatch, records: list[dict]):
    monkeypatch.chdir(tmp)
    raw = tmp / "raw"
    raw.mkdir()
    (raw / "t.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    manifest = tmp / "manifest.json"
    dl.download("t.jsonl", raw, manifest)
    st.run(raw / "t.jsonl", manifest, tmp / "d.duckdb", tmp / "none.toml", tmp / "s.md")
    return manifest, tmp / "d.duckdb"


def validate(tmp: Path, manifest: Path, db: Path):
    return va.run("t.jsonl", manifest, db, GATE, tmp / "none.toml", tmp / "g.md")


@pytest.mark.parametrize(("corruption", "reason"), CASES)
def test_corrupted_record_gets_the_right_reason(tmp_path, monkeypatch, corruption, reason):
    records = [good(i) for i in range(200)]
    bad = copy.deepcopy(records[7])
    corruption(bad)
    records[7] = bad
    manifest, db = build(tmp_path, monkeypatch, records)
    res = validate(tmp_path, manifest, db)
    assert not res.aborted  # 1 of 200 is 0.5 percent
    got = {r: n for r, n, _ in res.by_reason}
    assert got[reason] >= 1
    assert sum(got.values()) == got[reason]  # and no other reason fired
    con = duckdb.connect(str(db))
    assert con.execute("SELECT count(*) FROM clean_release").fetchone()[0] == 199
    assert con.execute("SELECT count(*) FROM clean_award").fetchone()[0] == 199


def test_clean_data_has_no_rejects(tmp_path, monkeypatch):
    manifest, db = build(tmp_path, monkeypatch, [good(i) for i in range(50)])
    res = validate(tmp_path, manifest, db)
    assert res.rejected_processes == 0 and not res.aborted
    assert "passed" in (tmp_path / "g.md").read_text()


def test_more_than_two_percent_aborts_and_leaves_no_clean_views(tmp_path, monkeypatch, capsys):
    records = [good(i) for i in range(100)]
    for i in (3, 9, 27):  # 3 of 100 is 3 percent
        corrupt_negative(records[i])
    manifest, db = build(tmp_path, monkeypatch, records)
    res = validate(tmp_path, manifest, db)
    assert res.aborted and res.rejected_processes == 3
    con = duckdb.connect(str(db))
    views = {r[0] for r in con.execute("SELECT view_name FROM duckdb_views()").fetchall()}
    assert "clean_release" not in views
    assert "ABORTED" in (tmp_path / "g.md").read_text()
    args = ["validate", "--file", "t.jsonl", "--manifest", str(manifest), "--db", str(db)]
    code = main([*args, "--gate", str(GATE), "--expected", "none.toml", "--out", "o.md"])
    assert code == 3
    assert "ABORT" in capsys.readouterr().out


def test_award_date_outside_window_is_flagged_not_rejected(tmp_path, monkeypatch):
    records = [good(i) for i in range(100)]
    records[1]["awards"][0]["date"] = "2017-06-01"
    del records[2]["awards"][0]["date"]
    manifest, db = build(tmp_path, monkeypatch, records)
    res = validate(tmp_path, manifest, db)
    assert res.rejected_processes == 0
    assert res.flagged_award_dates == 2


def test_stage_from_another_file_is_refused(tmp_path, monkeypatch):
    manifest, db = build(tmp_path, monkeypatch, [good(i) for i in range(10)])
    data = json.loads(manifest.read_text())
    data["files"]["t.jsonl"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(va.StageMismatch):
        validate(tmp_path, manifest, db)


def test_report_never_prints_identifiers(tmp_path, monkeypatch):
    records = [good(i) for i in range(200)]
    records[5]["buyer"]["id"] = "RSSMRA80A01H501U"  # shaped like a natural person's fiscal code
    records[6]["buyer"]["id"] = "12345678901"
    manifest, db = build(tmp_path, monkeypatch, records)
    res = validate(tmp_path, manifest, db)
    report = (tmp_path / "g.md").read_text()
    assert "RSSMRA80A01H501U" not in report and "12345678901" not in report
    assert "buyer <16-character code>" in report and "buyer <11-digit id>" in report
    assert res.rejected_processes == 2
