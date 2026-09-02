#!/usr/bin/env python3
"""Build a source-backed options knowledge layer from approved text pages."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HTML_TAG = re.compile(r"<[^>]+>")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode()).hexdigest()[:20]
    return f"{prefix}.{digest}"


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def normalize_text(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        line = IMAGE.sub("", line)
        line = LINK.sub(r"\1", line)
        line = HTML_TAG.sub("", line)
        line = html.unescape(line)
        line = re.sub(r"^\s*[-*+]\s+", "- ", line)
        line = re.sub(r"[`*_]+", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def sectionize(markdown: str) -> list[dict]:
    lines = markdown.splitlines()
    sections = []
    heading = None
    heading_level = None
    start_line = None
    body = []

    def flush(end_line: int) -> None:
        if heading is None:
            return
        text = normalize_text("\n".join(body))
        if text:
            sections.append({
                "heading": heading,
                "heading_level": heading_level,
                "line_start": start_line,
                "line_end": end_line,
                "text": text,
            })

    for line_number, line in enumerate(lines, start=1):
        match = HEADING.match(line)
        if match:
            flush(line_number - 1)
            heading_level = len(match.group(1))
            heading = match.group(2).strip()
            start_line = line_number
            body = []
        else:
            body.append(line)
    flush(len(lines))
    return sections


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def source_documents(index: dict, catalog: dict, raw_dir: Path, minimum_chars: int) -> tuple[dict, list[dict]]:
    index_documents = {document["id"]: document for document in index["documents"]}
    catalog_documents = catalog.get("documents", [])
    catalog_ids = [document["source_document_id"] for document in catalog_documents]
    if len(catalog_ids) != len(set(catalog_ids)):
        raise ValueError("Source catalog contains duplicate source_document_id values")
    if set(catalog_ids) != set(index_documents):
        raise ValueError("Source catalog and raw index must contain exactly the same documents")

    documents = {}
    rejected = []
    for entry in catalog_documents:
        document_id = entry["source_document_id"]
        indexed = index_documents[document_id]
        markdown_path = raw_dir / f"{document_id}.md"
        if not markdown_path.exists():
            raise ValueError(f"Missing raw Markdown evidence: {markdown_path}")
        markdown = markdown_path.read_text()
        body_chars = len(normalize_text(markdown))
        record = {
            **entry,
            "title": indexed["title"],
            "url": indexed["url"],
            "markdown_path": str(markdown_path),
            "markdown": markdown,
            "body_chars": body_chars,
            "content_hash": content_hash(markdown),
        }
        if entry["body_eligible"]:
            if body_chars < minimum_chars:
                raise ValueError(f"Eligible source is below the knowledge text minimum: {document_id}")
            documents[document_id] = record
        else:
            rejected.append(record)
    return documents, rejected


def build_chunks(documents: dict) -> list[dict]:
    chunks = []
    for document_id, document in documents.items():
        excluded_sections = {heading.lower() for heading in document.get("excluded_sections", [])}
        for section in sectionize(document["markdown"]):
            if section["heading"].lower() in excluded_sections:
                continue
            if not section["text"]:
                continue
            chunk_id = stable_id("chunk", document_id, section["heading"], section["text"])
            chunks.append({
                "id": chunk_id,
                "source_document_id": document_id,
                "source_id": document["source_id"],
                "source_url": document["url"],
                "knowledge_type": document["knowledge_type"],
                "title": document["title"],
                "heading": section["heading"],
                "heading_level": section["heading_level"],
                "line_start": section["line_start"],
                "line_end": section["line_end"],
                "text": section["text"],
                "content_hash": content_hash(section["text"]),
                "status": "reviewed",
            })
    chunks.sort(key=lambda chunk: (chunk["source_document_id"], chunk["line_start"], chunk["id"]))
    if not chunks:
        raise ValueError("No eligible text sections produced knowledge chunks")
    if len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise ValueError("Duplicate knowledge chunk IDs")
    # Identical boilerplate can appear on different OIC strategy pages; only reject
    # duplicate text within the same source document.
    by_document = {}
    for chunk in chunks:
        by_document.setdefault(chunk["source_document_id"], []).append(chunk["content_hash"])
    for document_id, hashes in by_document.items():
        if len(hashes) != len(set(hashes)):
            raise ValueError(f"Duplicate knowledge chunk content in {document_id}")
    return chunks


def evidence_for(chunks: list[dict], source_document_id: str, headings: list[str]) -> list[dict]:
    wanted = set(headings)
    matched = [chunk for chunk in chunks if chunk["source_document_id"] == source_document_id and chunk["heading"] in wanted]
    missing = wanted - {chunk["heading"] for chunk in matched}
    if missing:
        raise ValueError(f"Missing evidence sections for {source_document_id}: {sorted(missing)}")
    return [{
        "chunk_id": chunk["id"],
        "source_document_id": chunk["source_document_id"],
        "source_url": chunk["source_url"],
        "heading": chunk["heading"],
        "line_start": chunk["line_start"],
        "line_end": chunk["line_end"],
        "quote": chunk["text"][:320],
    } for chunk in matched]


def build_items(specs: dict, chunks: list[dict], allowed_types: set[str]) -> list[dict]:
    items = []
    for spec in specs.get("concepts", []):
        if spec["type"] not in allowed_types:
            raise ValueError(f"Unknown knowledge type in concept spec: {spec['type']}")
        evidence = evidence_for(chunks, spec["source_document_id"], spec["evidence_sections"])
        chosen_chunk_ids = {entry["chunk_id"] for entry in evidence}
        content = "\n\n".join(chunk["text"] for chunk in chunks if chunk["id"] in chosen_chunk_ids)
        items.append({
            "id": spec["id"],
            "type": spec["type"],
            "title": spec["title"],
            "aliases": spec["aliases"],
            "summary": spec["summary"],
            "terms": spec["terms"],
            "content": content,
            "evidence": evidence,
            "status": spec["status"],
        })
    items.sort(key=lambda item: item["id"])
    if len({item["id"] for item in items}) != len(items):
        raise ValueError("Duplicate knowledge item IDs")
    return items


def build_strategies(specs: dict, chunks: list[dict]) -> list[dict]:
    strategies = []
    required = {
        "legs", "market_outlook", "max_gain", "max_loss", "breakeven", "assignment_or_expiration_risk",
    }
    for spec in specs.get("strategies", []):
        if not required <= set(spec):
            raise ValueError(f"Strategy is missing required fields: {spec['id']}")
        evidence = {
            field: evidence_for(chunks, spec["source_document_id"], headings)
            for field, headings in spec["evidence_sections"].items()
        }
        missing_evidence = required - set(evidence)
        if missing_evidence:
            raise ValueError(f"Strategy has no evidence mapping: {spec['id']} {sorted(missing_evidence)}")
        strategies.append({
            key: value for key, value in spec.items() if key not in {"source_document_id", "evidence_sections"}
        } | {
            "source_document_id": spec["source_document_id"],
            "evidence": evidence,
        })
    strategies.sort(key=lambda strategy: strategy["id"])
    if len({strategy["id"] for strategy in strategies}) != len(strategies):
        raise ValueError("Duplicate strategy IDs")
    return strategies


def build_relations(specs: dict, chunks: list[dict], record_ids: set[str], relation_types: set[str]) -> list[dict]:
    relations = []
    for spec in specs.get("relations", []):
        if spec["from_id"] not in record_ids or spec["to_id"] not in record_ids:
            raise ValueError(f"Relation references an unknown knowledge record: {spec}")
        if spec["relation_type"] not in relation_types:
            raise ValueError(f"Unknown relation type: {spec['relation_type']}")
        evidence = evidence_for(chunks, spec["source_document_id"], spec["evidence_sections"])
        relation = {key: value for key, value in spec.items() if key not in {"source_document_id", "evidence_sections"}}
        relation["id"] = stable_id("relation", relation["from_id"], relation["relation_type"], relation["to_id"])
        relation["source_document_id"] = spec["source_document_id"]
        relation["evidence"] = evidence
        relations.append(relation)
    relations.sort(key=lambda relation: relation["id"])
    return relations


def build_evidence_index(items: list[dict], strategies: list[dict], relations: list[dict]) -> list[dict]:
    records = []
    for item in items:
        records.append({"knowledge_record_id": item["id"], "record_type": "item", "evidence": item["evidence"]})
    for strategy in strategies:
        evidence = [entry for entries in strategy["evidence"].values() for entry in entries]
        records.append({"knowledge_record_id": strategy["id"], "record_type": "strategy", "evidence": evidence})
    for relation in relations:
        records.append({"knowledge_record_id": relation["id"], "record_type": "relation", "evidence": relation["evidence"]})
    return sorted(records, key=lambda record: (record["record_type"], record["knowledge_record_id"]))


ARCHIVE_DIR = Path("archive/knowledge-json-2026-09-02")
INDEX_PATH = Path("data/raw/index.json")


def build_artifacts(root: Path, archive: Path, index_path: Path) -> dict:
    index = read_json(index_path)
    catalog = read_json(archive / "source-catalog.json")
    taxonomy = read_json(archive / "taxonomy.json")
    specs = read_json(archive / "knowledge-specs.json")
    minimum_chars = taxonomy["admission_rules"]["minimum_text_chars"]
    documents, rejected = source_documents(index, catalog, root / "data/raw/pages", minimum_chars)
    chunks = build_chunks(documents)
    allowed_types = {entry["id"] for entry in taxonomy["knowledge_types"]}
    items = build_items(specs, chunks, allowed_types)
    strategies = build_strategies(specs, chunks)
    record_ids = {item["id"] for item in items} | {strategy["id"] for strategy in strategies}
    relations = build_relations(specs, chunks, record_ids, set(taxonomy["relation_types"]))
    evidence_index = build_evidence_index(items, strategies, relations)
    catalog_summary = {
        "version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "architecture": {
            "evidence_layer": "data/raw/pages plus data/raw/index.json",
            "knowledge_layer": "archived JSON plus the knowledge/ wiki vault",
            "strategy_layer": "knowledge/wiki/strategies",
            "relationship_layer": "wikilinks in vault notes",
            "provenance_layer": "archive/knowledge-json-2026-09-02/evidence-index.json"
        },
        "source_documents": {
            "total": len(index["documents"]),
            "body_eligible": len(documents),
            "catalog_only": len(rejected),
            "by_source": dict(sorted(Counter(document["source_id"] for document in index["documents"]).items()))
        },
        "knowledge_records": {
            "chunks": len(chunks),
            "items": len(items),
            "strategies": len(strategies),
            "relations": len(relations),
            "by_type": dict(sorted(Counter(item["type"] for item in items).items()))
        },
        "entry_points": {
            "taxonomy": str(archive / "taxonomy.json"),
            "source_catalog": str(archive / "source-catalog.json"),
            "chunks": str(archive / "chunks.jsonl"),
            "items": str(archive / "items.json"),
            "strategies": str(archive / "strategies.json"),
            "relations": str(archive / "relations.json"),
            "evidence_index": str(archive / "evidence-index.json")
        }
    }
    return {
        "chunks": chunks,
        "items": items,
        "strategies": strategies,
        "relations": relations,
        "evidence_index": evidence_index,
        "catalog": catalog_summary,
    }


def validate_artifacts(artifacts: dict) -> None:
    chunks = {chunk["id"]: chunk for chunk in artifacts["chunks"]}
    if len(chunks) != len(artifacts["chunks"]):
        raise ValueError("Duplicate chunk IDs in artifacts")
    for record in artifacts["evidence_index"]:
        for evidence in record["evidence"]:
            chunk = chunks.get(evidence["chunk_id"])
            if chunk is None:
                raise ValueError(f"Evidence references unknown chunk: {evidence['chunk_id']}")
            if evidence["quote"] not in chunk["text"]:
                raise ValueError(f"Evidence quote does not occur in chunk: {evidence['chunk_id']}")
    if artifacts["catalog"]["knowledge_records"]["chunks"] != len(chunks):
        raise ValueError("Catalog chunk count is inconsistent")


def write_artifacts(archive: Path, artifacts: dict) -> None:
    archive.mkdir(parents=True, exist_ok=True)
    chunks_text = "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in artifacts["chunks"])
    (archive / "chunks.jsonl").write_text(chunks_text)
    write_json(archive / "items.json", {"version": 1, "items": artifacts["items"]})
    write_json(archive / "strategies.json", {"version": 1, "strategies": artifacts["strategies"]})
    write_json(archive / "relations.json", {"version": 1, "relations": artifacts["relations"]})
    write_json(archive / "evidence-index.json", {"version": 1, "records": artifacts["evidence_index"]})
    write_json(archive / "catalog.json", artifacts["catalog"])


def self_check() -> None:
    sections = sectionize("# Title\n\nIntro [link](https://example.com).\n\n### Detail\n\n![image](x.png) Some *text*.")
    assert [section["heading"] for section in sections] == ["Title", "Detail"]
    assert sections[0]["text"] == "Intro link."
    assert sections[1]["text"] == "Some text."
    assert stable_id("chunk", "a", "b") == stable_id("chunk", "a", "b")
    assert stable_id("chunk", "a", "b") != stable_id("chunk", "a", "c")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the archived JSON knowledge layer. The live product is the knowledge/ vault.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--archive", type=Path, default=ARCHIVE_DIR)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--check", action="store_true", help="Validate sources and build artifacts without writing them")
    args = parser.parse_args()
    root = args.root.resolve()
    archive = args.archive if args.archive.is_absolute() else root / args.archive
    index_path = args.index if args.index.is_absolute() else root / args.index
    self_check()
    artifacts = build_artifacts(root, archive, index_path)
    validate_artifacts(artifacts)
    if args.check:
        print(json.dumps({
            "ok": True,
            "chunks": len(artifacts["chunks"]),
            "items": len(artifacts["items"]),
            "strategies": len(artifacts["strategies"]),
            "relations": len(artifacts["relations"]),
        }))
        return
    write_artifacts(archive, artifacts)
    print(f"Rebuilt archived JSON: {len(artifacts['chunks'])} chunks, {len(artifacts['items'])} items, and {len(artifacts['strategies'])} strategies")


if __name__ == "__main__":
    main()
