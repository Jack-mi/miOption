"""Read-only vault lookup for wiki_query. Never writes, ingests, or rebuilds indexes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VAULT = REPO_ROOT / "knowledge"
DEFAULT_OBSIDIAN = REPO_ROOT / "vendor" / "claude-obsidian"
SEARCH_DIRS = ("wiki/strategies", "wiki/concepts")
SEARCH_FILES = ("wiki/index.md", "wiki/hot.md")
META_PREFIX = "wiki/meta/"
MAX_SNIPPET = 480
MAX_TOP = 20


def wiki_page(page_path: str) -> dict[str, Any]:
    vault = vault_root()
    path = (vault / page_path).resolve()
    if not path.is_relative_to(vault / "wiki") or path.suffix != ".md" or not path.is_file():
        raise ValueError("page_not_found")
    return {"page_path": path.relative_to(vault).as_posix(), "content": path.read_text(encoding="utf-8")}


def vault_root() -> Path:
    raw = os.environ.get("MIOPTION_VAULT") or str(DEFAULT_VAULT)
    return Path(raw).expanduser().resolve()


def obsidian_root() -> Path:
    raw = os.environ.get("MIOPTION_OBSIDIAN_ROOT") or str(DEFAULT_OBSIDIAN)
    return Path(raw).expanduser().resolve()


def retrieve_script() -> Path:
    return obsidian_root() / "scripts" / "retrieve.py"


def _tokens(query: str) -> list[str]:
    parts = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", query.lower())
    return [p for p in parts if len(p) > 1]


def _snippet(text: str, terms: list[str]) -> str:
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    lower = body.lower()
    hit = -1
    for term in terms:
        hit = lower.find(term)
        if hit >= 0:
            break
    if hit < 0:
        hit = 0
    start = max(0, hit - 80)
    chunk = body[start : start + MAX_SNIPPET].strip()
    if start > 0:
        chunk = "…" + chunk
    if start + MAX_SNIPPET < len(body):
        chunk = chunk + "…"
    return chunk


def _score_page(path: Path, vault: Path, terms: list[str]) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    rel = path.relative_to(vault).as_posix()
    hay = f"{path.stem} {rel} {text}".lower()
    score = 0.0
    for term in terms:
        count = hay.count(term)
        if not count:
            continue
        weight = 8.0 if term in path.stem.lower() or term in rel.lower() else 1.0
        score += count * weight
    if score <= 0:
        return None
    return {
        "page_path": rel,
        "absolute_path": str(path),
        "score": score,
        "snippet": _snippet(text, terms),
        "not_payoff_evidence": rel.startswith(META_PREFIX),
    }


def fallback_search(query: str, top: int, vault: Path) -> dict[str, Any]:
    terms = _tokens(query)
    hits: list[dict[str, Any]] = []
    if not terms:
        return {
            "query": query,
            "strategy": "fallback-empty-query",
            "top_k": top,
            "candidates": [],
            "vault": str(vault),
            "note": "Query produced no searchable tokens.",
        }
    paths: list[Path] = []
    for rel in SEARCH_DIRS:
        folder = vault / rel
        if folder.is_dir():
            paths.extend(sorted(folder.glob("*.md")))
    for rel in SEARCH_FILES:
        page = vault / rel
        if page.is_file():
            paths.append(page)
    for path in paths:
        hit = _score_page(path, vault, terms)
        if hit:
            hits.append(hit)
    hits.sort(key=lambda row: float(row["score"]), reverse=True)
    return {
        "query": query,
        "strategy": "fallback-wiki-scan",
        "top_k": top,
        "candidates": hits[:top],
        "vault": str(vault),
        "note": (
            "BM25 retrieve was unavailable; scanned strategies/concepts plus "
            "index/hot. Do not invent P/L. Skip wiki/meta pages for payoff numbers."
        ),
    }


def _run_retrieve(query: str, top: int, vault: Path) -> dict[str, Any] | None:
    if os.environ.get("MIOPTION_WIKI_RETRIEVE", "1") == "0":
        return None
    script = retrieve_script()
    if not script.is_file():
        return None
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--vault",
                str(vault),
                query,
                "--top",
                str(top),
                "--no-rerank",
                "--explain",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(obsidian_root()),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    payload["vault"] = str(vault)
    for cand in payload.get("candidates") or []:
        if isinstance(cand, dict):
            rel = str(cand.get("page_path") or "")
            cand["not_payoff_evidence"] = rel.startswith(META_PREFIX)
    return payload


def wiki_query(query: str, top: int = 5) -> dict[str, Any]:
    q = str(query or "").strip()
    n = max(1, min(int(top or 5), MAX_TOP))
    vault = vault_root()
    if not q:
        return {
            "query": q,
            "strategy": "empty",
            "top_k": n,
            "candidates": [],
            "vault": str(vault),
            "note": "Provide a non-empty query.",
        }
    retrieved = _run_retrieve(q, n, vault)
    result = retrieved if retrieved and retrieved.get("candidates") else fallback_search(q, n, vault)
    for candidate in result.get("candidates", []):
        try:
            page = wiki_page(str(candidate.get("page_path") or ""))
            candidate["content"] = page["content"][:16000]
            candidate["content_truncated"] = len(page["content"]) > 16000
        except (OSError, ValueError):
            continue
    return result
