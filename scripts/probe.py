#!/usr/bin/env python3
"""Run bounded, allowlisted Apify crawls and store normalized records."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


TERMINAL_RUN_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
REUSED_INPUT_FIELDS = (
    "startUrls", "includeUrlGlobs", "crawlerType", "maxCrawlDepth", "maxCrawlPages", "maxResults",
    "saveMarkdown", "saveHtml", "proxyConfiguration", "respectRobotsTxtFile", "useSitemaps", "useLlmsTxt",
    "blockMedia", "maxConcurrency", "maxRequestRetries", "maxSessionRotations",
)


def cli(args: list[str]) -> str:
    result = subprocess.run(["apify", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def parse_json(output: str):
    starts = [position for position in (output.find("{"), output.find("[")) if position >= 0]
    if not starts:
        raise ValueError("No JSON object in Apify CLI output")
    return json.loads(output[min(starts) :])


def unwrap(payload: dict) -> dict:
    return payload.get("data", payload)


def normalized_prefix(prefix: str) -> str:
    return "/" + prefix.strip("/")


def path_matches_prefix(path: str, prefix: str) -> bool:
    prefix = normalized_prefix(prefix)
    return path == prefix or path.startswith(prefix + "/")


def allowed_sources(sources: list[dict]) -> list[dict]:
    return [source for source in sources if source.get("allowed")]


def source_hosts(source: dict) -> set[str]:
    sample_url = source.get("sample_url")
    if not sample_url:
        return set()
    hosts = {urlparse(sample_url).netloc}
    for host in source.get("allowed_hosts") or []:
        if host:
            hosts.add(host)
    return hosts


def source_for_url(url: str, sources: list[dict]) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"URL must be absolute HTTPS: {url}")
    for source in allowed_sources(sources):
        sample_url = source.get("sample_url")
        prefixes = source.get("include_prefixes")
        if not sample_url or not prefixes:
            raise ValueError(f"Allowed source has no complete allowlist: {source.get('id')}")
        if parsed.netloc in source_hosts(source) and any(path_matches_prefix(parsed.path, prefix) for prefix in prefixes):
            return source
    raise ValueError(f"URL is outside the approved source/path allowlist: {url}")


def validate_knowledge_url(url: str, knowledge_policy: dict) -> None:
    path = urlparse(url).path.lower()
    if any(fragment.lower() in path for fragment in knowledge_policy["excluded_url_fragments"]):
        raise ValueError(f"Video or media URL is outside the knowledge corpus: {url}")


def validate_knowledge_content(content: str, url: str, knowledge_policy: dict) -> None:
    if len(content) < knowledge_policy["minimum_text_chars"]:
        raise ValueError(f"Page lacks enough text for the knowledge corpus: {url}")
    lowered = content.lower()
    if any(marker.lower() in lowered for marker in knowledge_policy["excluded_content_markers"]):
        raise ValueError(f"Video, course, or navigation page is outside the knowledge corpus: {url}")


def validate_candidate(candidate: dict, knowledge_policy: dict) -> None:
    missing = [key for key in knowledge_policy["candidate_required_fields"] if key not in candidate]
    if missing:
        raise ValueError(f"Candidate is missing knowledge fields ({', '.join(missing)}): {candidate.get('url')}")
    if candidate.get("knowledge_eligible") is not True:
        raise ValueError(f"Candidate is not approved for the knowledge corpus: {candidate.get('url')}")
    if candidate.get("content_kind") not in knowledge_policy["eligible_content_kinds"]:
        raise ValueError(f"Candidate is not a text knowledge page: {candidate.get('url')}")
    if candidate.get("video") is not False:
        raise ValueError(f"Candidate may contain video or media content: {candidate.get('url')}")
    if not candidate.get("knowledge_type"):
        raise ValueError(f"Candidate has no knowledge target: {candidate.get('url')}")
    if not isinstance(candidate["expected_fields"], list) or not candidate["expected_fields"]:
        raise ValueError(f"Candidate has no expected knowledge fields: {candidate.get('url')}")


def doc_id(source_id: str, url: str) -> str:
    return hashlib.sha1(f"{source_id}:{url}".encode()).hexdigest()[:16]


def validate_config(config: dict) -> None:
    crawl_policy = config["crawl_policy"]
    knowledge_policy = config.get("knowledge_policy")
    required = (
        "sample_max_pages", "max_crawl_pages", "max_crawl_depth", "run_timeout_secs",
        "wait_timeout_secs", "estimated_cost_per_page_usd", "max_cost_usd", "min_content_chars",
        "manual_review_below_chars",
    )
    missing = [key for key in required if key not in crawl_policy]
    if missing:
        raise ValueError(f"Missing crawl policy fields: {', '.join(missing)}")
    if crawl_policy["max_crawl_depth"] != 0:
        raise ValueError("Only fixed URL batches are supported; max_crawl_depth must be 0")
    if not 0 < crawl_policy["sample_max_pages"] <= crawl_policy["max_crawl_pages"]:
        raise ValueError("Invalid page caps")
    if crawl_policy["wait_timeout_secs"] < crawl_policy["run_timeout_secs"]:
        raise ValueError("wait_timeout_secs must be at least run_timeout_secs")
    if crawl_policy["estimated_cost_per_page_usd"] <= 0 or crawl_policy["max_cost_usd"] <= 0:
        raise ValueError("Cost limits must be positive")
    if not isinstance(knowledge_policy, dict):
        raise ValueError("Missing knowledge policy")
    required_knowledge_fields = (
        "minimum_text_chars", "eligible_content_kinds", "candidate_required_fields", "excluded_url_fragments",
        "excluded_content_markers",
    )
    missing_knowledge_fields = [key for key in required_knowledge_fields if key not in knowledge_policy]
    if missing_knowledge_fields:
        raise ValueError(f"Missing knowledge policy fields: {', '.join(missing_knowledge_fields)}")
    if knowledge_policy["minimum_text_chars"] < crawl_policy["min_content_chars"]:
        raise ValueError("Knowledge text minimum cannot be lower than the crawl minimum")
    for source in allowed_sources(config["sources"]):
        source_for_url(source["sample_url"], config["sources"])


def allowed_url_globs(sources: list[dict]) -> list[str]:
    globs = []
    for source in allowed_sources(sources):
        sample = urlparse(source["sample_url"])
        hosts = sorted(source_hosts(source)) or [sample.netloc]
        for host in hosts:
            origin = f"{sample.scheme}://{host}"
            for prefix in source["include_prefixes"]:
                path = normalized_prefix(prefix)
                globs.append(f"{origin}{path}")
                globs.append(f"{origin}{path}/**")
    return globs


def selected_candidate_urls(
    candidate_file: Path, batch: str | None, knowledge_policy: dict, include_ingested: bool = False,
) -> list[str]:
    payload = json.loads(candidate_file.read_text())
    candidates = payload.get("candidates", payload) if isinstance(payload, dict) else payload
    if not isinstance(candidates, list):
        raise ValueError("Candidate file must contain a list or a candidates list")
    urls = []
    for candidate in candidates:
        status = candidate.get("crawl_status")
        allowed_statuses = {"approved"}
        if include_ingested:
            allowed_statuses.add("ingested")
        if status not in allowed_statuses:
            continue
        if batch is not None and candidate.get("batch") != batch:
            continue
        if candidate.get("allowed") is not True:
            raise ValueError(f"Approved candidate is not allowed: {candidate.get('url')}")
        if not include_ingested:
            validate_candidate(candidate, knowledge_policy)
        urls.append(candidate["url"])
    if not urls:
        raise ValueError("No approved candidates matched the requested batch")
    return list(dict.fromkeys(urls))


def build_input(config: dict, urls: list[str] | None = None, max_pages: int | None = None) -> dict:
    validate_config(config)
    crawl_policy = config["crawl_policy"]
    urls = list(dict.fromkeys(urls or [source["sample_url"] for source in allowed_sources(config["sources"])]))
    if not urls:
        raise ValueError("No URLs selected")
    for url in urls:
        source_for_url(url, config["sources"])
        validate_knowledge_url(url, config["knowledge_policy"])
    page_budget = crawl_policy["sample_max_pages"] if max_pages is None else max_pages
    if page_budget != len(urls):
        raise ValueError(f"Page budget ({page_budget}) must exactly match selected URLs ({len(urls)})")
    if not 0 < page_budget <= crawl_policy["max_crawl_pages"]:
        raise ValueError("Requested page count exceeds the configured cap")
    estimated_cost = page_budget * crawl_policy["estimated_cost_per_page_usd"]
    if estimated_cost > crawl_policy["max_cost_usd"]:
        raise ValueError(f"Estimated cost ${estimated_cost:.2f} exceeds the configured budget")
    crawler_types = {
        source_for_url(url, config["sources"]).get("crawler_type") or crawl_policy["crawler_type"]
        for url in urls
    }
    if len(crawler_types) != 1:
        raise ValueError(f"Selected URLs require mixed crawler types: {sorted(crawler_types)}")
    return {
        "startUrls": [{"url": url} for url in urls],
        "includeUrlGlobs": allowed_url_globs(config["sources"]),
        "crawlerType": next(iter(crawler_types)),
        "maxCrawlDepth": 0,
        "maxCrawlPages": page_budget,
        "maxResults": page_budget,
        "saveMarkdown": crawl_policy["save_markdown"],
        "saveHtml": crawl_policy["save_html"],
        "proxyConfiguration": crawl_policy["proxy"],
        "respectRobotsTxtFile": crawl_policy["respect_robots_txt"],
        "useSitemaps": False,
        "useLlmsTxt": False,
        "blockMedia": True,
        "maxConcurrency": crawl_policy["max_concurrency"],
        "maxRequestRetries": crawl_policy["max_request_retries"],
        "maxSessionRotations": crawl_policy["max_session_rotations"],
    }


def preview_input(config: dict, candidate_file: Path | None, batch: str | None, urls: list[str] | None, max_pages: int | None) -> dict:
    if candidate_file and urls:
        raise ValueError("Use either a candidate file or explicit URLs, not both")
    selected = selected_candidate_urls(candidate_file, batch, config["knowledge_policy"], include_ingested=True) if candidate_file else urls
    return build_input(config, selected, max_pages)


def get_run(run_id: str) -> dict:
    return unwrap(parse_json(cli(["runs", "info", run_id, "--json"])))


def actor_id(actor: str) -> str:
    return unwrap(parse_json(cli(["actors", "info", actor, "--json"])))["id"]


def validate_run(run: dict, crawl_policy: dict) -> None:
    if run.get("status") != "SUCCEEDED" or run.get("exitCode") != 0:
        raise ValueError(f"Apify run did not succeed: {run.get('status')} (exit {run.get('exitCode')})")
    if not run.get("finishedAt") or not run.get("defaultDatasetId"):
        raise ValueError("Completed run is missing completion or dataset metadata")
    cost = run.get("usageTotalUsd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost):
        raise ValueError("Completed run is missing a numeric cost")
    if cost > crawl_policy["max_cost_usd"]:
        raise ValueError(f"Run cost ${cost:.4f} exceeded configured budget ${crawl_policy['max_cost_usd']:.2f}")


def wait_for_run(run_id: str, crawl_policy: dict) -> None:
    try:
        cli(["runs", "wait", run_id, "--timeout", str(crawl_policy["wait_timeout_secs"]), "--json"])
    except RuntimeError as error:
        try:
            if get_run(run_id).get("status") not in TERMINAL_RUN_STATUSES:
                cli(["runs", "abort", run_id, "--force", "--json"])
        except RuntimeError:
            pass
        raise RuntimeError(f"Run {run_id} was not accepted; any still-active run was aborted: {error}") from error


def validate_items(
    items: list[dict], sources: list[dict], requested_urls: list[str], crawl_policy: dict, knowledge_policy: dict,
) -> None:
    if len(items) != len(requested_urls):
        raise ValueError(f"Expected {len(requested_urls)} results, received {len(items)}")
    observed_requests = set()
    for item in items:
        if not isinstance(item, dict) or not item.get("url"):
            raise ValueError("Dataset contains an invalid item")
        source_for_url(item["url"], sources)
        validate_knowledge_url(item["url"], knowledge_policy)
        crawl = item.get("crawl") or {}
        loaded_url = crawl.get("loadedUrl", item["url"])
        source_for_url(loaded_url, sources)
        validate_knowledge_url(loaded_url, knowledge_policy)
        status = crawl.get("httpStatusCode")
        if not isinstance(status, int) or not 200 <= status < 300:
            raise ValueError(f"Dataset item did not return a successful HTTP status: {item['url']}")
        content = (item.get("markdown") or item.get("text") or "").strip()
        if len(content) < crawl_policy["min_content_chars"]:
            raise ValueError(f"Dataset item is too short to be useful: {item['url']}")
        validate_knowledge_content(content, item["url"], knowledge_policy)
        observed_requests.add(crawl.get("referrerUrl", item["url"]))
    if observed_requests != set(requested_urls):
        raise ValueError("Dataset results do not exactly match the requested URL batch")


def normalize_item(item: dict, sources: list[dict], run_id: str, crawl_policy: dict) -> dict:
    source = source_for_url(item["url"], sources)
    metadata = {key: value for key, value in (item.get("metadata") or {}).items() if key != "headers"}
    content = (item.get("markdown") or item.get("text") or "").strip()
    return {
        "id": doc_id(source["id"], item["url"]),
        "source_id": source["id"],
        "source_name": source["name"],
        "url": item["url"],
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "language": metadata.get("languageCode"),
        "text": item.get("text"),
        "markdown": item.get("markdown"),
        "crawl": item.get("crawl"),
        "metadata": metadata,
        "run_id": run_id,
        "quality": {
            "content_chars": len(content),
            "requires_manual_review": len(content) < crawl_policy["manual_review_below_chars"],
        },
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def existing_documents(index_path: Path) -> list[dict]:
    return json.loads(index_path.read_text()).get("documents", []) if index_path.exists() else []


def run_summary(run: dict, actor_input: dict, documents: list[dict]) -> dict:
    return {
        "version": 1,
        "run_id": run["id"],
        "status": run["status"],
        "exit_code": run["exitCode"],
        "started_at": run.get("startedAt"),
        "finished_at": run.get("finishedAt"),
        "cost_usd": run["usageTotalUsd"],
        "page_budget": actor_input["maxCrawlPages"],
        "documents": [{"id": document["id"], "url": document["url"]} for document in documents],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def store_documents(run: dict, actor_input: dict, documents: list[dict], out_dir: Path, index_path: Path) -> list[dict]:
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    index_documents = {document["id"]: document for document in existing_documents(index_path)}
    for document in documents:
        page_path = pages_dir / f"{document['id']}.json"
        markdown_path = pages_dir / f"{document['id']}.md"
        page_path.write_text(json.dumps(document, ensure_ascii=False, indent=2))
        markdown_path.write_text(document.get("markdown") or document.get("text") or "")
        index_documents[document["id"]] = {
            "id": document["id"], "source_id": document["source_id"], "source_name": document["source_name"],
            "url": document["url"], "title": document["title"], "description": document["description"],
            "language": document["language"], "page_path": str(page_path), "markdown_path": str(markdown_path),
            "run_id": document["run_id"], "quality": document["quality"], "ingested_at": document["ingested_at"],
        }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps({
        "version": 2, "latest_run_id": run["id"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": sorted(index_documents.values(), key=lambda document: document["id"]),
    }, ensure_ascii=False, indent=2))
    summaries_dir = out_dir.parent / "run-summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    (summaries_dir / f"{run['id']}.json").write_text(
        json.dumps(run_summary(run, actor_input, documents), ensure_ascii=False, indent=2) + "\n"
    )
    return documents


def run_probe(
    config: dict, out_dir: Path, index_path: Path, run_id: str | None = None,
    urls: list[str] | None = None, max_pages: int | None = None,
) -> list[dict]:
    actor_input = build_input(config, urls, max_pages)
    crawl_policy = config["crawl_policy"]
    requested_urls = [entry["url"] for entry in actor_input["startUrls"]]
    reused = run_id is not None
    if not reused:
        indexed_urls = {document["url"] for document in existing_documents(index_path)}
        repeated_urls = sorted(set(requested_urls) & indexed_urls)
        if repeated_urls:
            raise ValueError(f"Selected URLs already exist in the index; use --run-id to recover a completed run: {repeated_urls}")
    if not reused:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as input_file:
            json.dump(actor_input, input_file)
            input_file.flush()
            started_payload = unwrap(parse_json(cli([
                "actors", "start", config["actor"], "--input-file", input_file.name,
                "--timeout", str(crawl_policy["run_timeout_secs"]), "--json",
            ])))
        started = started_payload.get("run", started_payload)
        run_id = started["id"]
        wait_for_run(run_id, crawl_policy)
    run = get_run(run_id)
    if reused:
        if run.get("actId") != actor_id(config["actor"]):
            raise ValueError("Requested run belongs to a different actor")
        prior_input = parse_json(cli(["key-value-stores", "get-value", run["defaultKeyValueStoreId"], "INPUT"]))
        if any(prior_input.get(field) != actor_input.get(field) for field in REUSED_INPUT_FIELDS):
            raise ValueError("Requested run input does not match the current safety policy")
    validate_run(run, crawl_policy)
    items = parse_json(cli([
        "datasets", "get-items", run["defaultDatasetId"], "--format", "json", "--limit", str(len(requested_urls) + 1),
    ]))
    validate_items(items, config["sources"], requested_urls, crawl_policy, config["knowledge_policy"])
    documents = [normalize_item(item, config["sources"], run_id, crawl_policy) for item in items]
    return store_documents(run, actor_input, documents, out_dir, index_path)


def expect_value_error(callback) -> None:
    try:
        callback()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def self_check() -> None:
    config = {
        "actor": "apify/website-content-crawler",
        "crawl_policy": {
            "sample_max_pages": 1, "max_crawl_pages": 2, "max_crawl_depth": 0,
            "crawler_type": "playwright:adaptive", "save_markdown": True, "save_html": False,
            "proxy": {"useApifyProxy": True}, "respect_robots_txt": True, "max_concurrency": 1,
            "max_request_retries": 1, "max_session_rotations": 0, "run_timeout_secs": 60,
            "wait_timeout_secs": 90, "estimated_cost_per_page_usd": 0.03, "max_cost_usd": 0.06,
            "min_content_chars": 3, "manual_review_below_chars": 5,
        },
        "knowledge_policy": {
            "minimum_text_chars": 3,
            "eligible_content_kinds": ["article"],
            "candidate_required_fields": ["knowledge_eligible", "knowledge_type", "content_kind", "video", "expected_fields"],
            "excluded_url_fragments": ["/video/"],
            "excluded_content_markers": ["video lessons"],
        },
        "sources": [
            {"id": "oic", "name": "OIC", "allowed": True, "sample_url": "https://www.optionseducation.org/a", "include_prefixes": ["/a", "/education"]},
            {"id": "no", "name": "No", "allowed": False},
        ],
    }
    actor_input = build_input(config)
    assert actor_input["maxCrawlPages"] == 1
    assert actor_input["includeUrlGlobs"] == [
        "https://www.optionseducation.org/a",
        "https://www.optionseducation.org/a/**",
        "https://www.optionseducation.org/education",
        "https://www.optionseducation.org/education/**",
    ]
    assert source_for_url("https://www.optionseducation.org/education/x", config["sources"])["id"] == "oic"
    expect_value_error(lambda: source_for_url("http://www.optionseducation.org/a", config["sources"]))
    expect_value_error(lambda: source_for_url("https://www.optionseducation.org/educationx", config["sources"]))
    expect_value_error(lambda: build_input(config, ["https://www.optionseducation.org/a", "https://www.optionseducation.org/education/x"], 1))
    run = {"status": "SUCCEEDED", "exitCode": 0, "finishedAt": "now", "defaultDatasetId": "dataset", "usageTotalUsd": 0.03}
    validate_run(run, config["crawl_policy"])
    expect_value_error(lambda: validate_run({**run, "status": "FAILED"}, config["crawl_policy"]))
    expect_value_error(lambda: validate_run({**run, "usageTotalUsd": 0.07}, config["crawl_policy"]))
    item = {"url": "https://www.optionseducation.org/a", "text": "hello", "metadata": {"headers": {"set-cookie": "do-not-store"}}, "crawl": {"loadedUrl": "https://www.optionseducation.org/a", "referrerUrl": "https://www.optionseducation.org/a", "httpStatusCode": 200}}
    validate_items([item], config["sources"], [item["url"]], config["crawl_policy"], config["knowledge_policy"])
    assert "headers" not in normalize_item(item, config["sources"], "run", config["crawl_policy"])["metadata"]
    expect_value_error(lambda: validate_items([{**item, "url": "https://example.com/a"}], config["sources"], [item["url"]], config["crawl_policy"], config["knowledge_policy"]))
    expect_value_error(lambda: validate_knowledge_url("https://www.optionseducation.org/video/example", config["knowledge_policy"]))
    expect_value_error(lambda: validate_knowledge_content("video lessons", item["url"], config["knowledge_policy"]))
    validate_candidate({
        "url": item["url"], "knowledge_eligible": True, "knowledge_type": "concept", "content_kind": "article",
        "video": False, "expected_fields": ["definition"],
    }, config["knowledge_policy"])
    expect_value_error(lambda: validate_candidate({"url": item["url"]}, config["knowledge_policy"]))
    assert parse_json("\napplication/json\n[{\"ok\": true}]\n") == [{"ok": True}]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("sources.json"))
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--index", type=Path, default=Path("data/raw/index.json"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run-id", help="Reuse a completed run only when its exact input matches")
    parser.add_argument("--candidate-file", type=Path, help="Candidate JSON file")
    parser.add_argument("--batch", help="Approved candidate batch to run")
    parser.add_argument("--url", action="append", help="Preview an HTTPS URL only; new crawls must use reviewed candidates")
    parser.add_argument("--max-pages", type=int, help="Must exactly equal the selected URL count")
    parser.add_argument("--print-input", action="store_true", help="Validate and print the Actor input without starting a run")
    args = parser.parse_args()
    if args.check:
        self_check()
        print("ok")
        return
    if args.candidate_file and args.url:
        parser.error("Use either --candidate-file or --url, not both")
    if args.batch and not args.candidate_file:
        parser.error("--batch requires --candidate-file")
    if args.url and not args.print_input:
        parser.error("New crawls must use a reviewed candidate batch, not direct URLs")
    config = json.loads(args.config.read_text())
    if args.print_input:
        print(json.dumps(preview_input(config, args.candidate_file, args.batch, args.url, args.max_pages), ensure_ascii=False, indent=2))
        return
    urls = selected_candidate_urls(args.candidate_file, args.batch, config["knowledge_policy"]) if args.candidate_file else args.url
    documents = run_probe(config, args.out, args.index, args.run_id, urls, args.max_pages)
    print(f"Stored {len(documents)} documents in {args.index}")


if __name__ == "__main__":
    main()
