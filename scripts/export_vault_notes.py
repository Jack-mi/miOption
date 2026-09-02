#!/usr/bin/env python3
"""Export archived JSON knowledge cards into a claude-obsidian vault."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor/claude-obsidian"))

from claude_obsidian.ledgers import (  # noqa: E402
    CLAIM_SCHEMA,
    SOURCE_SCHEMA,
    stable_source_id,
)


ARCHIVE_DEFAULT = ROOT / "archive/knowledge-json-2026-09-02"
VAULT_DEFAULT = ROOT / "knowledge"
PAGES_DEFAULT = ROOT / "data/raw/pages"
INDEX_DEFAULT = ROOT / "data/raw/index.json"
CREATED = "2026-09-02"
GENERATED_AT = "2026-09-02T01:50:00Z"
REFRESH_DUE = "2027-09-02"
UNSAFE_NAME = re.compile(r'[/\\:*?"<>|]+')

STATUS_MAP = {
    "published": "evergreen",
    "reviewed": "developing",
    "draft": "seed",
}

RELATION_LABEL = {
    "requires": "requires",
    "affects": "affects",
    "defines": "defines",
    "related_to": "related to",
}


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if text == "" or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    if text.lower() in {"true", "false", "null", "yes", "no", "on", "off"}:
        return json.dumps(text, ensure_ascii=False)
    if text[:1] in "-?:@&*!|>%'\"`":
        return json.dumps(text, ensure_ascii=False)
    if any(ch in text for ch in ":#{}[],&*!|>%@`'\n\t"):
        return json.dumps(text, ensure_ascii=False)
    return text


def emit_frontmatter(fields: dict) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def note_filename(title: str, used: set[str], fallback: str) -> str:
    stem = UNSAFE_NAME.sub("-", title).strip(" .") or fallback
    candidate = f"{stem}.md"
    if candidate.casefold() not in used:
        used.add(candidate.casefold())
        return candidate
    extra = f"{stem} ({fallback}).md"
    if extra.casefold() not in used:
        used.add(extra.casefold())
        return extra
    raise ValueError(f"Cannot make unique note name for {title!r} / {fallback!r}")


def iso_date(value: str | None) -> str | None:
    if not value:
        return None
    return str(value)[:10]


def wiki_status(status: str) -> str:
    return STATUS_MAP.get(status, "developing")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def evidence_block(entries: list[dict], title_by_doc: dict[str, str]) -> str:
    if not entries:
        return "_No paragraph evidence recorded._\n"
    lines = []
    for entry in entries:
        source_title = title_by_doc.get(entry["source_document_id"])
        source_link = f"[[{source_title}]]" if source_title else entry.get("source_url", "")
        quote = (entry.get("quote") or "").replace("\n", " ").strip()
        lines.append(
            f"- {source_link} · `{entry.get('heading', '')}` · lines {entry.get('line_start')}–{entry.get('line_end')}"
        )
        if quote:
            lines.append(f"  > {quote}")
    return "\n".join(lines) + "\n"


def flatten_strategy_evidence(evidence: dict) -> list[dict]:
    rows = []
    for field, entries in evidence.items():
        for entry in entries:
            item = dict(entry)
            item["field"] = field
            rows.append(item)
    return rows


def related_section(record_id: str, relations_by_id: dict, title_by_id: dict) -> str:
    related = relations_by_id.get(record_id, [])
    if not related:
        return ""
    lines = ["## See also", ""]
    for rel in related:
        other_id = rel["other_id"]
        other_title = title_by_id.get(other_id, other_id)
        label = RELATION_LABEL.get(rel["relation_type"], rel["relation_type"])
        direction = "outbound" if rel["direction"] == "from" else "inbound"
        lines.append(f"- {label} ({direction}): [[{other_title}]]")
    lines.append("")
    return "\n".join(lines)


def source_note_title(document: dict, catalog_entry: dict) -> str:
    title = (document.get("title") or "").strip() or document["id"]
    prefix = "Source — "
    if catalog_entry.get("body_eligible"):
        return f"{prefix}{title}"
    return f"{prefix}{title} (catalog only)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=ARCHIVE_DEFAULT)
    parser.add_argument("--vault", type=Path, default=VAULT_DEFAULT)
    parser.add_argument("--pages", type=Path, default=PAGES_DEFAULT)
    parser.add_argument("--index", type=Path, default=INDEX_DEFAULT)
    args = parser.parse_args()

    archive = args.archive.resolve()
    vault = args.vault.resolve()
    pages_dir = args.pages.resolve()
    index = read_json(args.index.resolve())
    catalog = read_json(archive / "source-catalog.json")
    items = read_json(archive / "items.json")["items"]
    strategies = read_json(archive / "strategies.json")["strategies"]
    relations = read_json(archive / "relations.json")["relations"]
    coverage = read_json(archive / "strategy-coverage.json")

    catalog_by_id = {entry["source_document_id"]: entry for entry in catalog["documents"]}
    index_by_id = {document["id"]: document for document in index["documents"]}

    used_names: set[str] = {"index.md", "log.md", "hot.md", "overview.md"}
    source_dir = vault / "wiki/sources"
    concept_dir = vault / "wiki/concepts"
    strategy_dir = vault / "wiki/strategies"
    captured_dir = vault / ".raw/captured"
    for path in (source_dir, concept_dir, strategy_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    captured_dir.mkdir(parents=True, exist_ok=True)

    source_files: dict[str, dict] = {}
    title_by_doc: dict[str, str] = {}
    captured_by_doc: dict[str, str] = {}
    manifest_sources: dict[str, dict] = {}
    ledger_sources: dict[str, dict] = {}

    for document_id, document in sorted(index_by_id.items()):
        catalog_entry = catalog_by_id[document_id]
        md_path = pages_dir / f"{document_id}.md"
        if not md_path.exists():
            raise SystemExit(f"Missing raw Markdown: {md_path}")
        digest = sha256_file(md_path)
        stored_rel = f".raw/captured/{digest}.md"
        stored = vault / stored_rel
        if not stored.exists():
            shutil.copyfile(md_path, stored)
        captured_by_doc[document_id] = stored_rel
        title = source_note_title(document, catalog_entry)
        filename = note_filename(title, used_names, document_id)
        wiki_rel = f"wiki/sources/{filename}"
        title_by_doc[document_id] = Path(filename).stem
        source_files[document_id] = {
            "document": document,
            "catalog": catalog_entry,
            "filename": filename,
            "wiki_rel": wiki_rel,
            "title": Path(filename).stem,
            "digest": digest,
            "stored_rel": stored_rel,
        }
        ingested = iso_date(document.get("ingested_at"))
        eligible = bool(catalog_entry.get("body_eligible"))
        origin = {"kind": "url", "locator": document["url"]}
        source_id = stable_source_id("url", document["url"], digest)
        ledger_sources[source_id] = {
            "origin": origin,
            "content_kind": "webpage",
            "title": Path(filename).stem,
            "authority": "official" if document.get("source_id") in {"oic", "cboe", "cme"} else "secondary",
            "content_sha256": digest,
            "ingested_at": ingested,
            "retrieved_at": ingested,
            "refresh_due": REFRESH_DUE if eligible else None,
            "review_status": "active" if eligible else "unreviewed",
            "independence_key": document.get("source_id"),
            "pages": [wiki_rel],
            "supersedes": None,
        }
        manifest_sources[stored_rel] = {
            "hash": digest,
            "ingested_at": ingested or CREATED,
            "pages_created": [wiki_rel],
        }

    title_by_id: dict[str, str] = {}
    concept_files: dict[str, dict] = {}
    strategy_files: dict[str, dict] = {}

    for item in items:
        filename = note_filename(item["title"], used_names, item["id"])
        title_by_id[item["id"]] = Path(filename).stem
        concept_files[item["id"]] = {
            "item": item,
            "filename": filename,
            "wiki_rel": f"wiki/concepts/{filename}",
            "title": Path(filename).stem,
        }

    coverage_by_id = {}
    for category in coverage["categories"]:
        for card in category.get("cards", []):
            coverage_by_id[card["id"]] = {
                "futu_name_en": category["futu_name_en"],
                "futu_name_zh": category["futu_name_zh"],
                "coverage_status": category.get("status"),
            }

    for strategy in strategies:
        filename = note_filename(strategy["name"], used_names, strategy["id"])
        title_by_id[strategy["id"]] = Path(filename).stem
        strategy_files[strategy["id"]] = {
            "strategy": strategy,
            "filename": filename,
            "wiki_rel": f"wiki/strategies/{filename}",
            "title": Path(filename).stem,
            "coverage": coverage_by_id.get(strategy["id"], {}),
        }

    relations_by_id: dict[str, list[dict]] = defaultdict(list)
    for relation in relations:
        relations_by_id[relation["from_id"]].append(
            {
                "relation_type": relation["relation_type"],
                "other_id": relation["to_id"],
                "direction": "from",
                "evidence": relation.get("evidence", []),
            }
        )
        relations_by_id[relation["to_id"]].append(
            {
                "relation_type": relation["relation_type"],
                "other_id": relation["from_id"],
                "direction": "to",
                "evidence": relation.get("evidence", []),
            }
        )

    cited_sources: dict[str, set[str]] = defaultdict(set)
    for item in items:
        for entry in item.get("evidence", []):
            cited_sources[entry["source_document_id"]].add(title_by_id[item["id"]])
    for strategy in strategies:
        for entry in flatten_strategy_evidence(strategy.get("evidence", {})):
            cited_sources[entry["source_document_id"]].add(title_by_id[strategy["id"]])
        source_document_id = strategy.get("source_document_id")
        if source_document_id:
            cited_sources[source_document_id].add(title_by_id[strategy["id"]])

    for document_id, meta in source_files.items():
        catalog_entry = meta["catalog"]
        document = meta["document"]
        eligible = bool(catalog_entry.get("body_eligible"))
        tags = ["source", document.get("source_id", "unknown")]
        if not eligible:
            tags.append("catalog-only")
        citing = sorted(cited_sources.get(document_id, []))
        fields = {
            "type": "source",
            "title": meta["title"],
            "status": "evergreen" if eligible else "developing",
            "created": CREATED,
            "updated": CREATED,
            "tags": tags,
            "source_type": catalog_entry.get("content_kind", "article"),
            "url": document.get("url", ""),
            "source_id": document.get("source_id", ""),
            "sha256": meta["digest"],
            "authority": "official" if document.get("source_id") in {"oic", "cboe", "cme"} else "secondary",
            "independence_key": document.get("source_id", ""),
            "review_state": "active" if eligible else "unreviewed",
        }
        body = [
            f"# {meta['title']}",
            "",
            catalog_entry.get("reason") or document.get("description") or "",
            "",
            f"- Publisher: {document.get('source_name', document.get('source_id'))}",
            f"- Body eligible: {'yes' if eligible else 'no'}",
            f"- Knowledge type: {catalog_entry.get('knowledge_type')}",
            f"- Crawl document id: `{document_id}`",
            f"- Immutable capture: `{meta['stored_rel']}`",
            f"- Crawl original: `data/raw/pages/{document_id}.md`",
            "",
            "## Used by",
            "",
        ]
        if citing:
            body.extend(f"- [[{title}]]" for title in citing)
        else:
            body.append("- Not cited by a published knowledge or strategy card.")
        body.extend(["", "See the [[index|Wiki Index]].", ""])
        (source_dir / meta["filename"]).write_text(
            emit_frontmatter(fields) + "\n".join(body)
        )

    for record_id, meta in concept_files.items():
        item = meta["item"]
        source_titles = []
        seen = set()
        for entry in item.get("evidence", []):
            title = title_by_doc.get(entry["source_document_id"])
            if title and title not in seen:
                source_titles.append(title)
                seen.add(title)
        related_titles = [
            title_by_id[rel["other_id"]]
            for rel in relations_by_id.get(record_id, [])
            if rel["other_id"] in title_by_id
        ]
        fields = {
            "type": "concept",
            "title": meta["title"],
            "status": wiki_status(item.get("status", "reviewed")),
            "created": CREATED,
            "updated": CREATED,
            "tags": ["concept", item.get("type", "concept")],
            "domain": "options",
            "aliases": item.get("aliases") or [],
            "sources": [f"[[{title}]]" for title in source_titles],
            "related": [f"[[{title}]]" for title in related_titles],
        }
        body = [
            f"# {meta['title']}",
            "",
            item.get("summary") or "",
            "",
            "## Terms",
            "",
        ]
        terms = item.get("terms") or []
        if terms:
            body.extend(f"- {term}" for term in terms)
        else:
            body.append("- None listed.")
        body.extend(["", "## Content", "", item.get("content") or "", "", "## Evidence", ""])
        body.append(evidence_block(item.get("evidence") or [], title_by_doc))
        body.append(related_section(record_id, relations_by_id, title_by_id))
        body.extend(["See the [[index|Wiki Index]].", ""])
        (concept_dir / meta["filename"]).write_text(
            emit_frontmatter(fields) + "\n".join(body)
        )

    for record_id, meta in strategy_files.items():
        strategy = meta["strategy"]
        coverage_meta = meta["coverage"]
        source_titles = []
        seen = set()
        if strategy.get("source_document_id"):
            title = title_by_doc.get(strategy["source_document_id"])
            if title:
                source_titles.append(title)
                seen.add(title)
        for entry in flatten_strategy_evidence(strategy.get("evidence") or {}):
            title = title_by_doc.get(entry["source_document_id"])
            if title and title not in seen:
                source_titles.append(title)
                seen.add(title)
        related_titles = [
            title_by_id[rel["other_id"]]
            for rel in relations_by_id.get(record_id, [])
            if rel["other_id"] in title_by_id
        ]
        tags = ["entity", "strategy"]
        if coverage_meta.get("futu_name_en"):
            tags.append(coverage_meta["futu_name_en"].replace(" ", "-").lower())
        fields = {
            "type": "entity",
            "title": meta["title"],
            "status": wiki_status(strategy.get("status", "reviewed")),
            "created": CREATED,
            "updated": CREATED,
            "tags": tags,
            "entity_type": "option-strategy",
            "aliases": strategy.get("aliases") or [],
            "sources": [f"[[{title}]]" for title in source_titles],
            "related": [f"[[{title}]]" for title in related_titles],
        }
        legs = strategy.get("legs") or []
        body = [
            f"# {meta['title']}",
            "",
            strategy.get("objective") or "",
            "",
            f"- Underlying: {strategy.get('underlying') or 'unspecified'}",
            f"- Knowledge id: `{strategy['id']}`",
            f"- Review status: `{strategy.get('status')}`",
        ]
        if coverage_meta:
            body.append(
                f"- Futu category: {coverage_meta.get('futu_name_zh')} / {coverage_meta.get('futu_name_en')}"
            )
        if strategy.get("status") == "reviewed":
            body.extend(
                [
                    "",
                    "> Draft: this card stays `reviewed` until a dedicated diagonal source exists, or P/L fields are rewritten to diagonal (not calendar) evidence.",
                ]
            )
        body.extend(["", "## Legs", ""])
        if legs:
            for leg in legs:
                body.append(
                    f"- {leg.get('position')} {leg.get('quantity')} ({leg.get('instrument')})"
                )
        else:
            body.append("- None listed.")
        body.extend(
            [
                "",
                "## Meaning",
                "",
                strategy.get("objective") or "",
                "",
                "## Scenario",
                "",
                strategy.get("market_outlook") or "",
                "",
                strategy.get("suitability_constraints") or "",
                "",
                "## Method",
                "",
                f"- Max gain: {strategy.get('max_gain') or ''}",
                f"- Max loss: {strategy.get('max_loss') or ''}",
                f"- Breakeven: {strategy.get('breakeven') or ''}",
                f"- Assignment / expiration: {strategy.get('assignment_or_expiration_risk') or ''}",
                "",
                "## Greeks and time",
                "",
                f"- Volatility: {strategy.get('volatility_effect') or ''}",
                f"- Time decay: {strategy.get('time_decay_effect') or ''}",
                "",
                "## Evidence",
                "",
            ]
        )
        by_field = strategy.get("evidence") or {}
        if by_field:
            for field, entries in by_field.items():
                body.append(f"### {field.replace('_', ' ').title()}")
                body.append("")
                body.append(evidence_block(entries, title_by_doc))
        else:
            body.append("_No paragraph evidence recorded._")
            body.append("")
        body.append(related_section(record_id, relations_by_id, title_by_id))
        body.extend(["See the [[index|Wiki Index]].", ""])
        (strategy_dir / meta["filename"]).write_text(
            emit_frontmatter(fields) + "\n".join(body)
        )

    coverage_lines = [
        emit_frontmatter(
            {
                "type": "meta",
                "title": "Futu strategy coverage",
                "status": "evergreen",
                "created": CREATED,
                "updated": CREATED,
                "tags": ["meta", "coverage"],
            }
        ),
        "# Futu strategy coverage",
        "",
        coverage.get("purpose") or "",
        "",
        "The menu follows Futu; the evidence is OIC text pages, not Futu pages.",
        "",
    ]
    for category in coverage["categories"]:
        coverage_lines.append(f"## {category['futu_name_zh']} / {category['futu_name_en']}")
        coverage_lines.append("")
        coverage_lines.append(f"Category status: `{category.get('status')}`.")
        coverage_lines.append("")
        for card in category.get("cards", []):
            title = title_by_id.get(card["id"], card.get("name", card["id"]))
            coverage_lines.append(f"- [[{title}]] — `{card.get('status')}`")
        coverage_lines.append("")
    skip = coverage.get("skip") or []
    if skip:
        coverage_lines.extend(["## Skipped", ""])
        for entry in skip:
            coverage_lines.append(
                f"- {entry.get('futu_name_zh')} / {entry.get('futu_name_en')}: {entry.get('reason')}"
            )
        coverage_lines.append("")
    (vault / "wiki/meta/Futu strategy coverage.md").write_text("\n".join(coverage_lines))

    source_links = [f"- [[{meta['title']}]]" for meta in sorted(source_files.values(), key=lambda item: item["title"].casefold())]
    concept_links = [f"- [[{meta['title']}]]" for meta in sorted(concept_files.values(), key=lambda item: item["title"].casefold())]
    entity_links = [f"- [[{meta['title']}]]" for meta in sorted(strategy_files.values(), key=lambda item: item["title"].casefold())]
    index_text = emit_frontmatter(
        {
            "type": "meta",
            "title": "Wiki Index",
            "status": "evergreen",
            "created": CREATED,
            "updated": CREATED,
            "tags": ["meta", "index"],
        }
    ) + "\n".join(
        [
            "# Wiki Index",
            "",
            "miOption options knowledge: source-backed concepts and named strategies.",
            "",
            "## Sources",
            "",
            *source_links,
            "",
            "## Concepts",
            "",
            *concept_links,
            "",
            "## Entities",
            "",
            *entity_links,
            "",
            "## Coverage",
            "",
            "- [[Futu strategy coverage]]",
            "",
            "## Questions",
            "",
            "- No questions indexed yet.",
            "",
        ]
    )
    (vault / "wiki/index.md").write_text(index_text)

    overview_text = emit_frontmatter(
        {
            "type": "overview",
            "title": "Vault Overview",
            "status": "evergreen",
            "created": CREATED,
            "updated": CREATED,
            "tags": ["overview"],
        }
    ) + "\n".join(
        [
            "# Vault Overview",
            "",
            "This vault is the miOption options knowledge base. URLs and raw pages are evidence, not the product.",
            "",
            "## Scope",
            "",
            "- Include option concepts, pricing, Greeks, lifecycle, strategies, and option-focused courses.",
            "- Include options on futures when the material is about option contracts and their risk or pricing.",
            "- Exclude standalone futures education, videos, webinars, course catalogs, and marketing pages from usable knowledge.",
            "- Do not add stock-picking or timing calls as named strategy cards.",
            "",
            "## Layers",
            "",
            "1. Crawl evidence stays in `data/raw/pages/` (outside the vault).",
            "2. Immutable copies used by vault skills live in `.raw/captured/`.",
            "3. Source notes, concepts, and strategy entities live in `wiki/`.",
            "",
            f"- Source notes: {len(source_files)}",
            f"- Concept notes: {len(concept_files)}",
            f"- Strategy entities: {len(strategy_files)}",
            f"- Published relations migrated as wikilinks: {len(relations)}",
            "",
            "See [[index]], [[Futu strategy coverage]], and [[log]].",
            "",
        ]
    )
    (vault / "wiki/overview.md").write_text(overview_text)

    log_text = emit_frontmatter(
        {
            "type": "meta",
            "title": "Wiki Log",
            "status": "evergreen",
            "created": CREATED,
            "updated": CREATED,
            "tags": ["meta", "log"],
        }
    ) + "\n".join(
        [
            "# Wiki Log",
            "",
            "## 2026-09-02 — Import archived JSON knowledge",
            "",
            "Migrated the JSON knowledge layer into this vault:",
            "",
            f"- {len(source_files)} source notes from admitted crawl pages",
            f"- {len(concept_files)} concept notes from published items",
            f"- {len(strategy_files)} strategy entities from strategy cards",
            f"- {len(relations)} relations rewritten as wikilinks",
            "",
            "`strategy.diagonal_spread` remains developing until dedicated diagonal evidence exists.",
            "",
        ]
    )
    (vault / "wiki/log.md").write_text(log_text)

    hot_text = emit_frontmatter(
        {
            "type": "meta",
            "title": "Hot Cache",
            "status": "developing",
            "created": CREATED,
            "updated": CREATED,
            "tags": ["meta", "hot-cache"],
        }
    ) + "\n".join(
        [
            "# Recent Context",
            "",
            "## Last Updated",
            "",
            "JSON knowledge cards were imported into wiki notes on 2026-09-02.",
            "",
            "## Key Recent Facts",
            "",
            "- Knowledge product is this Obsidian vault, not `items.json`.",
            "- Futu App menu ∪ topic474 is one coverage set; 27 strategy entities are evergreen.",
            "- Diagonal / Strap / Strip publish structure; numeric P/L stays blank where sources do not publish it.",
            "",
            "## Recent Changes",
            "",
            "- Initialized claude-obsidian vault under `knowledge/`.",
            "- Imported published concepts, strategies, sources, and relations.",
            "",
            "## Active Threads",
            "",
            "- Keep P/L fields source-bound; do not invent textbook formulas for Diagonal / Strap / Strip.",
            "",
        ]
    )
    (vault / "wiki/hot.md").write_text(hot_text)

    claude_md = "\n".join(
        [
            "# miOption vault",
            "",
            "This directory is the user-owned Obsidian vault. Product code lives in `vendor/claude-obsidian`.",
            "",
            "## Constraints",
            "",
            "- Options education and strategy research only.",
            "- Keep claims tied to source notes and `.raw/captured/` payloads.",
            "- Do not crawl a whole site. New pages need an approved candidate batch.",
            "- Investopedia is excluded from automated crawling.",
            "- Do not promote Diagonal Call Spread to evergreen without dedicated evidence.",
            "",
            "## Layout",
            "",
            "- `inbox/` visible intake",
            "- `.raw/captured/` immutable source copies",
            "- `wiki/sources/` admitted pages",
            "- `wiki/concepts/` published knowledge items",
            "- `wiki/strategies/` named strategy entities",
            "",
        ]
    )
    (vault / "CLAUDE.md").write_text(claude_md)

    write_json(
        vault / ".raw/.manifest.json",
        {
            "address_map": {},
            "description": "Ingest delta tracker. Source payloads are create-only.",
            "sources": manifest_sources,
            "version": 1,
        },
    )
    write_json(
        vault / "wiki/meta/ledgers/source-ledger.json",
        {
            "schema": SOURCE_SCHEMA,
            "generated_at": GENERATED_AT,
            "sources": ledger_sources,
        },
    )
    write_json(
        vault / "wiki/meta/ledgers/claim-ledger.json",
        {
            "schema": CLAIM_SCHEMA,
            "generated_at": GENERATED_AT,
            "claims": {},
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "sources": len(source_files),
                "concepts": len(concept_files),
                "strategies": len(strategy_files),
                "relations": len(relations),
                "captured": len({meta["stored_rel"] for meta in source_files.values()}),
            }
        )
    )


if __name__ == "__main__":
    main()
