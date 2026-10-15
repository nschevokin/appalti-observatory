"""Download OCDS bulk files from the Open Contracting Partnership registry and pin each one by
sha256 in manifest.json, so every published number can be traced to the exact input files."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.request
from collections.abc import Callable
from pathlib import Path

BASE_URL = "https://data.open-contracting.org/en/publication/117/download?name="
CHUNK = 1 << 20


class ChecksumMismatch(Exception):
    """A file differs from the sha256 pinned in the manifest."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"source": BASE_URL + "<file>", "files": {}}


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def file_name_for(year: int | None = None, name: str | None = None) -> str:
    if name:
        return name
    return f"{year}.jsonl.gz" if year else "full.jsonl.gz"


def fetch(url: str, dest: Path) -> None:
    """Stream url to dest through a .part file, so a cut transfer never leaves a bad file."""
    part = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp, part.open("wb") as out:
        while chunk := resp.read(CHUNK):
            out.write(chunk)
    part.replace(dest)


def _record(manifest: dict, name: str, url: str, dest: Path, digest: str, adopted: bool) -> None:
    manifest["files"][name] = {
        "adopted": adopted,
        "bytes": dest.stat().st_size,
        "downloaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "sha256": digest,
        "url": url,
    }


def download(
    name: str,
    raw_dir: Path,
    manifest_path: Path,
    base_url: str = BASE_URL,
    fetcher: Callable[[str, Path], None] = fetch,
) -> str:
    """Make sure `name` is in raw_dir and pinned in the manifest.

    Returns 'downloaded', 'unchanged' (already there and matching the pin) or 'adopted' (a file
    that was already there got pinned, no network used). Raises ChecksumMismatch rather than
    silently replacing a file that differs from its pin.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / name
    manifest = load_manifest(manifest_path)
    entry = manifest["files"].get(name)
    url = base_url + name

    if dest.exists():
        digest = sha256_file(dest)
        if entry is None:
            _record(manifest, name, url, dest, digest, adopted=True)
            save_manifest(manifest_path, manifest)
            return "adopted"
        if entry["sha256"] != digest:
            raise ChecksumMismatch(f"{name}: file {digest} differs from pinned {entry['sha256']}")
        return "unchanged"

    fetcher(url, dest)
    digest = sha256_file(dest)
    if entry is not None and entry["sha256"] != digest:
        dest.unlink()
        raise ChecksumMismatch(f"{name}: download {digest} differs from pinned {entry['sha256']}")
    _record(manifest, name, url, dest, digest, adopted=False)
    save_manifest(manifest_path, manifest)
    return "downloaded"


def verify(raw_dir: Path, manifest_path: Path) -> list[str]:
    """Recompute every pinned hash; return a list of problems (empty means all good)."""
    problems = []
    for name, entry in load_manifest(manifest_path)["files"].items():
        path = raw_dir / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"{name}: sha256 differs from the manifest")
    return problems
