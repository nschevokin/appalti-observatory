"""Site build on the synthetic world, plus the CLI chain."""

import re

import pytest

from appalti import cli
from appalti import gate2 as g2
from appalti import site as sitemod
from appalti import status as statusmod
from tests.test_entities import ROOT, build_db, resolve
from tests.test_indicators import GATE_TOML, PROC, run_ind, world

PAGES = [
    "index.html", "awarded-value.html", "concentration.html", "procedure-mix.html",
    "single-bidder.html", "comparability.html", "quality.html", "method.html",
]  # fmt: skip


@pytest.fixture
def judged(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, world())
    resolve(tmp_path, manifest, db)
    run_ind(tmp_path, manifest, db)
    g2.check(db, GATE_TOML, tmp_path / "gate2.md")
    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "indicators.md").write_text("x")
    return tmp_path, db


def test_site_builds_every_page_with_the_refusal_panel(judged):
    tmp, db = judged
    pages = sitemod.build(db, tmp / "site", tmp / "ev")
    assert pages == PAGES
    for name in PAGES:
        assert (tmp / "site" / name).stat().st_size > 1000
    idx = (tmp / "site" / "index.html").read_text()
    assert 'class="refusal"' in idx and "not published." in idx
    assert "3.33 of the 2020 count, outside the accepted band of 0.5 to 2.0" in idx
    assert (tmp / "site" / "evidence" / "indicators.md").exists()


def test_every_page_states_the_gate1_exclusion_and_the_non_claims(judged):
    tmp, db = judged
    sitemod.build(db, tmp / "site", tmp / "ev")
    for name in PAGES:
        html = (tmp / "site" / name).read_text()
        assert "Gate 1 excluded" in html, name  # D031
        assert "not</em> spent" in html or "is not <em>spent</em>" in html, name


def test_no_javascript_no_external_resources_no_names(judged):
    tmp, db = judged
    sitemod.build(db, tmp / "site", tmp / "ev")
    for name in PAGES:
        html = (tmp / "site" / name).read_text()
        assert "<script" not in html and "http://" not in html
        assert not re.search(r'(src|href)="https?://(?!github.com)', html), name
        assert "ALFA" not in html and "11111111111" not in html


def test_build_is_deterministic(judged):
    tmp, db = judged
    sitemod.build(db, tmp / "a", tmp / "ev")
    sitemod.build(db, tmp / "b", tmp / "ev")
    for name in PAGES:
        assert (tmp / "a" / name).read_text() == (tmp / "b" / name).read_text()


def test_site_refuses_when_gate_never_judged(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, world())
    resolve(tmp_path, manifest, db)
    run_ind(tmp_path, manifest, db)  # indicators exist, Gate 2 never ran
    with pytest.raises(sitemod.SiteRefused):
        sitemod.build(db, tmp_path / "site", tmp_path / "ev")


def test_cli_chain_and_status(tmp_path, monkeypatch):
    manifest, db = build_db(tmp_path, monkeypatch, world())
    resolve(tmp_path, manifest, db)
    common = ["--db", str(db)]
    assert cli.main(["indicators", "--file", "t.jsonl", "--manifest", str(manifest), *common,
                     "--gate", str(GATE_TOML), "--proc", str(PROC),
                     "--out", str(tmp_path / "i.md")]) == 0  # fmt: skip
    assert cli.main(["gate", "check", *common, "--gate", str(GATE_TOML),
                     "--out", str(tmp_path / "g.md")]) == 0  # fmt: skip
    assert cli.main(["site", "build", *common, "--out", str(tmp_path / "s"),
                     "--evidence", str(tmp_path)]) == 0  # fmt: skip
    out = "\n".join(statusmod.lines(db))
    assert "gate_decision latest run" in out and "refused" in out
    assert ROOT.exists()
