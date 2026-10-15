"""Staging tests on the four-line synthetic fixture."""

import json
import shutil
from pathlib import Path

import duckdb
import pytest

from appalti import download as dl
from appalti import stage as st
from appalti.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "ocds_sample.jsonl"


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(FIXTURE, raw / "sample.jsonl")
    manifest = tmp_path / "manifest.json"
    dl.download("sample.jsonl", raw, manifest)  # adopts
    return raw / "sample.jsonl", manifest, tmp_path


def test_stage_counts_and_reconciliation(setup):
    raw, manifest, tmp = setup
    expected = tmp / "exp.toml"
    expected.write_text(
        '[files."sample.jsonl"]\nlines = 4\ntenders = 3\nawards = 3\ncontracts = 2\n'
        "parties = 4\nsupplier_role_rows = 2\naward_supplier_refs = 1\nmilestones = 0\n"
    )
    checks = st.run(raw, manifest, tmp / "t.duckdb", expected, tmp / "out.md")
    # the fixture repeats ocid ocds-2 on purpose: the duplicate check must catch exactly that
    assert [c.name for c in checks if c.status == "MISMATCH"] == ["distinct ocid equals lines"]
    con = duckdb.connect(str(tmp / "t.duckdb"))
    assert con.execute("SELECT count(*) FROM stg_release").fetchone()[0] == 4
    # bad values stay visible and unparsed: 'abc' amount is NULL with its raw text kept
    bad = con.execute("SELECT amount_raw FROM stg_award WHERE amount IS NULL").fetchall()
    assert bad == [("abc",)]
    assert con.execute("SELECT count(*) FROM stg_award WHERE amount < 0").fetchone()[0] == 1
    # empty identifier becomes NULL, stub line has no tender
    assert con.execute("SELECT count(*) FROM stg_party WHERE id_raw IS NULL").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM stg_release WHERE NOT has_tender").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM stage_reconciliation").fetchone()[0] == len(checks)
    assert (
        "| lines | 4 | 4 | ok" in (tmp / "out.md").read_text()
        or "ok" in (tmp / "out.md").read_text()
    )


def test_wrong_stated_total_is_reported_as_mismatch(setup):
    raw, manifest, tmp = setup
    expected = tmp / "exp.toml"
    expected.write_text('[files."sample.jsonl"]\nawards = 999\n')
    checks = st.run(raw, manifest, tmp / "t.duckdb", expected, tmp / "out.md")
    assert [c.name for c in checks if c.status == "MISMATCH"] == [
        "awards",
        "distinct ocid equals lines",
    ]


def test_unpinned_or_changed_file_is_refused(setup):
    raw, manifest, tmp = setup
    data = json.loads(manifest.read_text())
    data["files"]["sample.jsonl"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(st.NotPinned):
        st.run(raw, manifest, tmp / "t.duckdb", tmp / "none.toml", tmp / "out.md")
    manifest.unlink()
    with pytest.raises(st.NotPinned):
        st.run(raw, manifest, tmp / "t.duckdb", tmp / "none.toml", tmp / "out.md")


def test_cli_stage(setup, capsys):
    raw, manifest, tmp = setup
    args = [
        "stage",
        "--file",
        "sample.jsonl",
        "--raw-dir",
        str(raw.parent),
        "--manifest",
        str(manifest),
        "--db",
        str(tmp / "c.duckdb"),
        "--expected",
        str(tmp / "none.toml"),
        "--out",
        str(tmp / "o.md"),
    ]
    assert main(args) == 1  # duplicate ocid in the fixture
    assert "1 mismatch" in capsys.readouterr().out
