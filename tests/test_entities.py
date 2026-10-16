"""Entity and fact-table tests on a small synthetic file with known answers."""

import json
from pathlib import Path

import duckdb
import pytest

from appalti import audit as au
from appalti import download as dl
from appalti import entities as en
from appalti import stage as st
from appalti import validate as va
from tests.test_validate import GATE

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit.toml"
CAP = ROOT / "labels" / "cap_region.csv"

BUYER_ID = "80012345678"


def rec(
    i: int,
    suppliers: list[tuple[str, str, str]],
    year: int = 2021,
    postal: str = "20100",
    buyer_id: str = BUYER_ID,
    buyer_name: str = "COMUNE DI TEST",
    amount: float = 900.0,
    tender_amount: float = 1000.0,
    tenderers: int | None = None,
    tender_year: int | None = None,
    cod: int = 1,
    cpv: str | None = None,
) -> dict:
    parties = [
        {
            "id": buyer_id,
            "roles": ["buyer"],
            "name": buyer_name,
            "identifier": {"scheme": "IT-CF", "id": buyer_id},
            "address": {"postalCode": postal, "locality": "TESTVILLE"},
        }
    ]
    for pid, ident, name in suppliers:
        parties.append(
            {
                "id": pid,
                "roles": ["supplier"],
                "name": name,
                "identifier": {"scheme": "IT-CF", "id": ident},
            }
        )
    tender = {
        "value": {"amount": tender_amount, "currency": "EUR"},
        "tenderPeriod": {"startDate": f"{tender_year or year}-01-01"},
        "procurementMethodDetails": f"COD:{cod} ; TITLE:x",
    }
    if tenderers is not None:
        tender["numberOfTenderers"] = tenderers
    if cpv is not None:
        tender["items"] = [{"id": "1", "classification": {"scheme": "CPV", "id": f"{cpv}000000"}}]
    return {
        "ocid": f"o{i}",
        "id": f"r{i}",
        "tag": ["award"],
        "initiationType": "tender",
        "date": f"{year}-03-01T10:00:00Z",
        "tender": tender,
        "buyer": {"id": buyer_id},
        "parties": parties,
        "awards": [
            {
                "id": "a1",
                "date": f"{year}-02-01",
                "value": {"amount": amount, "currency": "EUR"},
                "suppliers": [{"id": p} for p, _, _ in suppliers],
            }
        ],
        "contracts": [{"id": "c1", "awardID": "a1"}],
    }


def build_db(tmp: Path, monkeypatch, records: list[dict], audit_path: Path = AUDIT):
    monkeypatch.chdir(tmp)
    raw = tmp / "raw"
    raw.mkdir(exist_ok=True)
    (raw / "t.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    manifest = tmp / "manifest.json"
    dl.download("t.jsonl", raw, manifest)
    db = tmp / "d.duckdb"
    st.run(raw / "t.jsonl", manifest, db, tmp / "none.toml", tmp / "s.md")
    res = va.run("t.jsonl", manifest, db, GATE, tmp / "none.toml", tmp / "g.md")
    assert not res.aborted
    return manifest, db


def resolve(tmp: Path, manifest: Path, db: Path, audit_path: Path = AUDIT):
    return en.run("t.jsonl", manifest, db, GATE, audit_path, CAP, tmp / "e.md")


def q(db: Path, sql: str):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def basic_records() -> list[dict]:
    acme = ("s1", "11111111111", "ACME SRL")
    recs = [
        rec(0, [acme], tenderers=1),
        rec(1, [acme], tenderers=3, postal="00100"),
        rec(2, [("s1", "11111111111", "ACME S.R.L.")], postal="2010"),  # malformed postal code
        rec(3, [acme]),
        rec(4, [("s2", "22222222222", "TWO SRL"), ("s3", "33333333333", "THREE SRL")]),
        rec(5, [("s4", "123", "SHORT SRL")]),
        rec(6, [("s4", "00000000123", "SHORT SRL")]),  # the padded form exists
        rec(7, [("s5", "999", "LONELY SRL")]),  # no padded form: stays as published
        rec(8, [("s6", BUYER_ID, "COMUNE DI TEST")]),  # a buyer that also supplies
        rec(9, [acme], amount=50000.0, tender_amount=1000.0),  # more than 10x its tender
    ]
    return recs


@pytest.fixture
def built(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, basic_records())
    res = resolve(tmp_path, manifest, db)
    return tmp_path, manifest, db, res


def test_checks_pass(built):
    _, _, _, res = built
    assert res.failed == []


def test_padding_only_when_the_padded_form_exists(built):
    _, _, db, _ = built
    keys = {r[0] for r in q(db, "SELECT DISTINCT key FROM party_key WHERE role = 'supplier'")}
    assert "IT-CF:00000000123" in keys and "IT-CF:123" not in keys
    assert "IT-CF:999" in keys


def test_canonical_name_is_the_most_frequent_spelling(built):
    _, _, db, _ = built
    rows = q(db, "SELECT canonical_name FROM entity WHERE identifier_id = '11111111111'")
    assert rows == [("ACME SRL",)]


def test_kind_both_and_method(built):
    _, _, db, _ = built
    assert q(db, f"SELECT kind, method FROM entity WHERE identifier_id = '{BUYER_ID}'") == [
        ("both", "identifier")
    ]


def test_entity_ids_are_deterministic(built, tmp_path, monkeypatch):
    first = q(built[2], "SELECT entity_id, entity_key FROM entity ORDER BY 1")
    other = tmp_path / "again"
    other.mkdir()
    manifest, db = build_db(other, monkeypatch, basic_records())
    resolve(other, manifest, db)
    assert q(db, "SELECT entity_id, entity_key FROM entity ORDER BY 1") == first


def test_supplier_bridge_splits_equally(built):
    _, _, db, _ = built
    shares = q(db, "SELECT share FROM fact_award_supplier WHERE ocid = 'o4'")
    assert sorted(s for (s,) in shares) == [0.5, 0.5]


def test_inconsistent_amount_flag(built):
    _, _, db, _ = built
    flagged = q(db, "SELECT ocid FROM fact_award WHERE inconsistent_amount")
    assert flagged == [("o9",)]


def test_single_bidder_is_null_when_not_published(built):
    _, _, db, _ = built
    got = dict(q(db, "SELECT ocid, single_bidder FROM fact_award WHERE ocid IN ('o0','o1','o3')"))
    assert got == {"o0": True, "o1": False, "o3": None}


def test_region_from_postal_prefix(built):
    _, _, db, _ = built
    got = dict(q(db, "SELECT ocid, region FROM fact_award WHERE ocid IN ('o0','o1','o2')"))
    assert got == {"o0": "Lombardia", "o1": "Lazio", "o2": "unknown"}


def test_report_has_no_identifier(built):
    tmp, _, _, _ = built
    text = (tmp / "e.md").read_text()
    for needle in ("11111111111", BUYER_ID, "ACME", "COMUNE DI TEST"):
        assert needle not in text


def test_unknown_apply_rule_is_refused():
    with pytest.raises(au.AuditError):
        au.build_alias_table(Path("nowhere.duckdb"), ["homonym"])
