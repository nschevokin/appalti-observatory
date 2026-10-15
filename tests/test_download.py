"""Tests for the download step. No internet: a local HTTP server stands in for the registry."""

import hashlib
import http.server
import json
import threading
from pathlib import Path

import pytest

from appalti import download as dl
from appalti.cli import main

PAYLOAD = b"line one\nline two\n"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


@pytest.fixture
def server():
    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", str(len(PAYLOAD)))
            self.end_headers()
            self.wfile.write(PAYLOAD)

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/download?name=", hits
    httpd.shutdown()


def test_first_download_pins_sha256(tmp_path: Path, server):
    base, hits = server
    manifest = tmp_path / "manifest.json"
    result = dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    assert result == "downloaded"
    entry = json.loads(manifest.read_text())["files"]["x.jsonl.gz"]
    assert entry["sha256"] == PAYLOAD_SHA
    assert entry["adopted"] is False
    assert len(hits) == 1


def test_rerun_fetches_nothing(tmp_path: Path, server):
    base, hits = server
    manifest = tmp_path / "manifest.json"
    dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    result = dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    assert result == "unchanged"
    assert len(hits) == 1


def test_existing_file_is_adopted_without_network(tmp_path: Path, server):
    base, hits = server
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "x.jsonl.gz").write_bytes(PAYLOAD)
    result = dl.download("x.jsonl.gz", raw, tmp_path / "manifest.json", base_url=base)
    assert result == "adopted"
    assert hits == []
    entry = json.loads((tmp_path / "manifest.json").read_text())["files"]["x.jsonl.gz"]
    assert entry["adopted"] is True and entry["sha256"] == PAYLOAD_SHA


def test_changed_file_is_refused_not_overwritten(tmp_path: Path, server):
    base, _ = server
    manifest = tmp_path / "manifest.json"
    dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    (tmp_path / "raw" / "x.jsonl.gz").write_bytes(b"tampered")
    with pytest.raises(dl.ChecksumMismatch):
        dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    assert (tmp_path / "raw" / "x.jsonl.gz").read_bytes() == b"tampered"


def test_redownload_that_differs_from_pin_is_rejected(tmp_path: Path, server):
    base, _ = server
    manifest = tmp_path / "manifest.json"
    dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    data = json.loads(manifest.read_text())
    data["files"]["x.jsonl.gz"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    (tmp_path / "raw" / "x.jsonl.gz").unlink()
    with pytest.raises(dl.ChecksumMismatch):
        dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    assert not (tmp_path / "raw" / "x.jsonl.gz").exists()


def test_verify_reports_missing_and_changed(tmp_path: Path, server):
    base, _ = server
    manifest = tmp_path / "manifest.json"
    dl.download("x.jsonl.gz", tmp_path / "raw", manifest, base_url=base)
    assert dl.verify(tmp_path / "raw", manifest) == []
    (tmp_path / "raw" / "x.jsonl.gz").write_bytes(b"other")
    assert "differs" in dl.verify(tmp_path / "raw", manifest)[0]
    (tmp_path / "raw" / "x.jsonl.gz").unlink()
    assert "missing" in dl.verify(tmp_path / "raw", manifest)[0]


def test_file_name_for():
    assert dl.file_name_for() == "full.jsonl.gz"
    assert dl.file_name_for(year=2025) == "2025.jsonl.gz"
    assert dl.file_name_for(name="2021.xlsx") == "2021.xlsx"


def test_cli_adopts_then_verifies(tmp_path: Path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "full.jsonl.gz").write_bytes(PAYLOAD)
    manifest = tmp_path / "manifest.json"
    args = ["download", "--raw-dir", str(raw), "--manifest", str(manifest)]
    assert main(args) == 0
    assert "adopted" in capsys.readouterr().out
    assert main([*args, "--verify"]) == 0
    (raw / "full.jsonl.gz").write_bytes(b"changed")
    assert main([*args, "--verify"]) == 1
    assert main(args) == 2
