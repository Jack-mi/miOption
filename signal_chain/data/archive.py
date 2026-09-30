"""Immutable local source bytes and privacy-safe remote research index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

from ..config import REPO_ROOT
from . import macro
from .http import post_json
from .keys import load_keys

TICKER = re.compile(r"US\.[A-Z0-9]+(?:\.[A-Z0-9]+)*")
RAW_DIRS = ("signals", "reports", "chains", "runs", "runtime/data/live/seller",
            "runtime/data/mock/seller", "runtime/data/archive", "runtime/data/live/archive",
            "runtime/data/mock/archive")


def archive_root() -> Path:
    return Path(os.environ.get("MIOPTION_ARCHIVE_DIR") or REPO_ROOT / "runtime/data/archive")


def preserve(path: Path) -> Path | None:
    """Copy existing bytes before a same-name overwrite, without changing the source."""
    if not path.is_file() or not path.resolve().is_relative_to(REPO_ROOT.resolve()):
        return None
    if path.resolve().is_relative_to(archive_root().resolve()):
        return path
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    relative = path.resolve().relative_to(REPO_ROOT.resolve())
    target = archive_root() / relative / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(content)
    target.chmod(0o600)
    return target


def inventory() -> list[Path]:
    paths = []
    for folder in RAW_DIRS:
        root = REPO_ROOT / folder
        paths.extend(path for path in root.rglob("*") if path.is_file() and
                     (path.suffix in {".json", ".jsonl", ".md"} or folder.endswith("/archive")))
    return sorted(set(paths))


def entry(path: Path) -> dict:
    origin = path.relative_to(REPO_ROOT).as_posix()
    content = path.read_bytes()
    source = origin
    if origin.startswith("runtime/data/archive/"):
        source = origin.removeprefix("runtime/data/archive/").rsplit("/", 1)[0]
    elif origin.startswith(("runtime/data/live/archive/", "runtime/data/mock/archive/")):
        prefix, source = origin.split("/archive/", 1)
        source = prefix + "/seller/" + source.rsplit("/", 1)[0]
    kind = "seller_" + Path(source).parent.name if "/seller/" in source else source.split("/", 1)[0]
    environment = "mock" if "/mock/" in source else "live" if "/live/" in source else "unknown"
    ticker = next(iter(TICKER.findall(origin)), None)
    return {"kind": kind, "ticker": ticker, "origin": origin,
            "digest": hashlib.sha256(content).hexdigest(), "observed_at": None,
            "quality": "legacy_unverified", "environment": environment,
            "payload": {"local_only": True, "bytes": len(content),
                        "reason": "original contains or may contain prices, account data or unlicensed quotes"}}


def quote_metadata(db: Path) -> list[dict]:
    if not db.exists():
        return []
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as connection:
        pulls = connection.execute("select id, underlying, source, pulled_at from pulls").fetchall()
    environment = db.parent.name
    return [{"kind": "quote_pull_metadata", "ticker": ticker,
             "origin": f"{db.relative_to(REPO_ROOT).as_posix()}#pull={pull_id}",
             "digest": hashlib.sha256(f"{db}:{pull_id}:{ticker}:{source}:{pulled_at}".encode()).hexdigest(),
             "observed_at": pulled_at, "quality": "legacy_unverified",
             "environment": environment,
             "payload": {"source": source, "local_only": True, "raw_quote_uploaded": False}}
            for pull_id, ticker, source, pulled_at in pulls]


def manifest() -> list[dict]:
    return ([entry(path) for path in inventory()] +
            [row for mode in ("live", "mock") for row in
             quote_metadata(REPO_ROOT / "runtime/data" / mode / "quotes.sqlite")])


def import_manifest(rows: list[dict], key: str, post=post_json) -> None:
    if not key:
        raise RuntimeError("missing SUPABASE_SERVICE_ROLE_KEY")
    url = macro.SUPABASE_URL + "/rest/v1/research_archive?on_conflict=kind,origin,digest"
    headers = {**macro._headers(key), "Prefer": "resolution=ignore-duplicates"}
    for index in range(0, len(rows), 100):
        post(url, headers, rows[index:index + 100])


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory and index old artifacts; raw bytes stay local")
    parser.add_argument("--apply", action="store_true", help="Preserve files locally and import metadata")
    args = parser.parse_args()
    rows = manifest()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    print(json.dumps({"count": len(rows), "kinds": counts, "raw_cloud_uploads": 0}, ensure_ascii=False))
    if args.apply:
        for path in inventory():
            if not path.resolve().is_relative_to(archive_root().resolve()) and "/archive/" not in path.relative_to(REPO_ROOT).as_posix():
                preserve(path)
        import_manifest(rows, load_keys()["SUPABASE_SERVICE_ROLE_KEY"])
        print("indexed", len(rows), "local snapshots preserved", len(inventory()))


if __name__ == "__main__":
    main()
