#!/usr/bin/env python3
"""Ingest winner-configured WCC batches for the four matched sites into data/raw."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import probe  # noqa: E402

BATCHES = [
    {
        "source_id": "optionistics",
        "urls": [
            "https://www.optionistics.com/s/chapter5/3_spreads.html",
            "https://www.optionistics.com/s/option_spreads",
            "https://www.optionistics.com/s/chapter5/7_butterflies_condors_and_wingspreads.html",
            "https://www.optionistics.com/s/chapter5/1_common_complex_strategies.html",
        ],
    },
    {
        "source_id": "opc",
        "urls": [
            "https://www.optionsprofitcalculator.com/faq.html",
            "https://www2.optionsprofitcalculator.com/calculator/diagonal-spread.html",
        ],
    },
    {
        "source_id": "optionstrat",
        "urls": [
            "https://optionstrat.com/tutorials/strategy-optimizer",
            "https://optionstrat.com/tutorials/options-builder",
        ],
    },
    {
        "source_id": "sharepredictions",
        "urls": [
            "https://sharepredictions.com/",
        ],
    },
]


def main() -> int:
    config = json.loads((ROOT / "sources.json").read_text())
    out_dir = ROOT / "data" / "raw"
    index_path = out_dir / "index.json"
    ledger_path = ROOT / "data" / "pipeline" / "apify-smoke-ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"budget_usd": 5.0, "spent_usd": 0.0, "runs": []}

    for batch in BATCHES:
        urls = batch["urls"]
        print(f"BATCH {batch['source_id']} n={len(urls)}", flush=True)
        documents = probe.run_probe(config, out_dir, index_path, urls=urls, max_pages=len(urls))
        # run_probe already wrote run summary; append cost into experiment ledger
        latest = json.loads(index_path.read_text())["latest_run_id"]
        summary = json.loads((ROOT / "data" / "run-summaries" / f"{latest}.json").read_text())
        cost = float(summary.get("cost_usd") or 0)
        ledger["runs"].append({
            "site": batch["source_id"],
            "spec": "batch-winner",
            "actor": config["actor"],
            "run_id": latest,
            "status": summary.get("status"),
            "cost_usd": cost,
            "chars": sum(d.get("quality", {}).get("content_chars", 0) for d in documents),
            "pass": True,
            "urls": urls,
        })
        ledger["spent_usd"] = round(float(ledger.get("spent_usd") or 0) + cost, 6)
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
        print(f"STORED {len(documents)} docs run={latest} cost=${cost:.4f} spent=${ledger['spent_usd']:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
