#!/usr/bin/env python3
"""Smoke-test Apify actors against four options sites. Tracks cost into the matrix ledger."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data/pipeline/apify-actor-matrix.md"
LEDGER = ROOT / "data/pipeline/apify-smoke-ledger.json"
BUDGET = 5.0


def cli(args: list[str]) -> dict | list | str:
    result = subprocess.run(["apify", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"apify {' '.join(args)} failed:\n{result.stderr or result.stdout}")
    out = result.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and len(payload) == 1:
        return payload["data"]
    return payload


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"budget_usd": BUDGET, "spent_usd": 0.0, "runs": []}


def save_ledger(ledger: dict) -> None:
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def spent(ledger: dict) -> float:
    return float(ledger.get("spent_usd") or 0.0)


def wcc_input(url: str, crawler_type: str) -> dict:
    return {
        "startUrls": [{"url": url}],
        "maxCrawlPages": 1,
        "maxCrawlDepth": 0,
        "maxConcurrency": 1,
        "maxRequestRetries": 1,
        "crawlerType": crawler_type,
        "proxyConfiguration": {"useApifyProxy": True},
        "respectRobotsTxtFile": True,
        "saveMarkdown": True,
        "saveHtml": False,
        "removeCookieWarnings": True,
        "blockMedia": True,
    }


def cheerio_input(url: str) -> dict:
    return {
        "startUrls": [{"url": url}],
        "maxRequestsPerCrawl": 1,
        "maxConcurrency": 1,
        "maxRequestRetries": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "pageFunction": """async function pageFunction(context) {
            const { $, request } = context;
            const title = ($('title').first().text() || '').trim();
            const text = ($('body').text() || '').replace(/\\s+/g, ' ').trim();
            return { url: request.url, title, text, textLength: text.length };
        }""",
    }


def web_scraper_input(url: str) -> dict:
    return {
        "startUrls": [{"url": url}],
        "maxRequestsPerCrawl": 1,
        "maxConcurrency": 1,
        "maxRequestRetries": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "pageFunction": """async function pageFunction(context) {
            const { request, log } = context;
            await context.waitFor(2000);
            const title = await context.page.title();
            const text = await context.page.evaluate(() => (document.body && document.body.innerText || '').replace(/\\s+/g, ' ').trim());
            return { url: request.url, title, text, textLength: text.length };
        }""",
    }


def playwright_input(url: str) -> dict:
    return {
        "startUrls": [{"url": url}],
        "maxRequestsPerCrawl": 1,
        "maxConcurrency": 1,
        "maxRequestRetries": 1,
        "proxyConfiguration": {"useApifyProxy": True},
        "pageFunction": """async function pageFunction(context) {
            const { page, request } = context;
            await page.waitForTimeout(2000);
            const title = await page.title();
            const text = await page.evaluate(() => (document.body && document.body.innerText || '').replace(/\\s+/g, ' ').trim());
            return { url: request.url, title, text, textLength: (text || '').length };
        }""",
    }


SPECS = {
    "wcc-cheerio": ("apify/website-content-crawler", lambda u: wcc_input(u, "cheerio")),
    "wcc-adaptive": ("apify/website-content-crawler", lambda u: wcc_input(u, "playwright:adaptive")),
    "wcc-firefox": ("apify/website-content-crawler", lambda u: wcc_input(u, "playwright:firefox")),
    "cheerio": ("apify/cheerio-scraper", cheerio_input),
    "web": ("apify/web-scraper", web_scraper_input),
    "playwright": ("apify/playwright-scraper", playwright_input),
}


def text_len_from_items(items: list, actor: str) -> tuple[int, str]:
    if not items:
        return 0, ""
    item = items[0]
    if actor.endswith("website-content-crawler"):
        text = item.get("text") or item.get("markdown") or ""
        title = (item.get("metadata") or {}).get("title") or item.get("url") or ""
        return len(text), str(title)[:120]
    text = item.get("text") or ""
    title = item.get("title") or item.get("url") or ""
    return len(text), str(title)[:120]


def run_one(site: str, url: str, spec_key: str, ledger: dict) -> dict:
    if spent(ledger) >= BUDGET:
        raise RuntimeError(f"Budget exhausted: ${spent(ledger):.4f} / ${BUDGET:.2f}")
    actor, builder = SPECS[spec_key]
    actor_input = builder(url)
    with tempfile.NamedTemporaryFile("w", suffix=".json") as fh:
        json.dump(actor_input, fh)
        fh.flush()
        started = unwrap(cli([
            "actors", "start", actor, "--input-file", fh.name,
            "--timeout", "300", "--json",
        ]))
    run = started.get("run", started)
    run_id = run["id"]
    print(f"STARTED {site} {spec_key} {run_id} {url}", flush=True)
    deadline = time.time() + 360
    while time.time() < deadline:
        info = unwrap(cli(["runs", "info", run_id, "--json"]))
        status = info.get("status")
        if status in {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}:
            break
        time.sleep(8)
    else:
        info = unwrap(cli(["runs", "info", run_id, "--json"]))
        status = info.get("status", "UNKNOWN")
    cost = float(info.get("usageTotalUsd") or 0.0)
    items = []
    title = ""
    chars = 0
    if status == "SUCCEEDED" and info.get("defaultDatasetId"):
        items = unwrap(cli([
            "datasets", "get-items", info["defaultDatasetId"], "--format", "json", "--limit", "5",
        ]))
        if not isinstance(items, list):
            items = []
        chars, title = text_len_from_items(items, actor)
    passed = status == "SUCCEEDED" and chars >= 500
    entry = {
        "site": site,
        "url": url,
        "spec": spec_key,
        "actor": actor,
        "run_id": run_id,
        "status": status,
        "cost_usd": cost,
        "chars": chars,
        "title": title,
        "pass": passed,
    }
    ledger["runs"].append(entry)
    ledger["spent_usd"] = round(spent(ledger) + cost, 6)
    save_ledger(ledger)
    print(f"DONE {json.dumps(entry, ensure_ascii=False)}", flush=True)
    print(f"SPENT ${ledger['spent_usd']:.4f} / ${BUDGET:.2f}", flush=True)
    return entry


# Ordered smoke plan: cheapest-first per site, stop early on pass.
PLAN = [
    ("optionistics", "https://www.optionistics.com/s/chapter5/3_spreads.html", ["wcc-cheerio", "cheerio", "wcc-adaptive"]),
    ("opc", "https://www.optionsprofitcalculator.com/calculator/diagonal-spread.html", ["wcc-adaptive", "wcc-firefox", "web"]),
    ("optionstrat", "https://optionstrat.com/tutorials/strategy-optimizer", ["wcc-firefox", "wcc-adaptive", "web"]),
    ("sharepredictions", "https://sharepredictions.com/", ["wcc-adaptive", "cheerio", "web"]),
]


def main() -> int:
    ledger = load_ledger()
    already = {(r["site"], r["spec"], r["url"]) for r in ledger.get("runs", [])}
    for site, url, specs in PLAN:
        site_passed = any(r["site"] == site and r.get("pass") for r in ledger.get("runs", []))
        if site_passed:
            print(f"SKIP {site}: already has a passing smoke", flush=True)
            continue
        for spec in specs:
            key = (site, spec, url)
            if key in already:
                print(f"SKIP already ran {key}", flush=True)
                # if that prior run passed, break
                prior = next(r for r in ledger["runs"] if (r["site"], r["spec"], r["url"]) == key)
                if prior.get("pass"):
                    break
                continue
            if spent(ledger) >= BUDGET - 0.05:
                print("Budget nearly exhausted; stopping smoke plan", flush=True)
                return 0
            entry = run_one(site, url, spec, ledger)
            if entry["pass"]:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
