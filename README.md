# miOption options knowledge base

This project builds a local knowledge base from public options-education sources.

## Current status

- A 4-page smoke test and a 12-page fixed-URL pilot have completed successfully; `knowledge/index.json` currently contains 16 normalized documents.
- Crawl scope is enforced in code: HTTPS-only source/path allowlists, fixed URL batches, depth `0`, robots.txt checks, and post-run validation of page count, status, source path, and cost.
- Investopedia is excluded from automated crawling because its robots/terms prohibit automated scraping and AI dataset use.
- Complete Apify run metadata is local-only and ignored by Git because it can contain signed URLs and runtime secrets. The repository contains only sanitized run summaries.

## Layout

- `sources.json` — source policy, limits, and source/path allowlists
- `knowledge/url-candidates.json` / `.csv` — reviewed crawl candidates and batch status (`ingested` pages cannot be re-run normally)
- `scripts/probe.py` — bounded Apify crawl runner
- `data/raw/pages/` — normalized public page records
- `data/run-summaries/` — committed sanitized run summaries
- `data/raw/runs/` — ignored local-only complete run metadata
- `knowledge/index.json` — generated document index

## Verify and preview a batch

```bash
python3 scripts/probe.py --check
python3 scripts/probe.py \
  --candidate-file knowledge/url-candidates.json \
  --batch next \
  --max-pages 3 \
  --print-input
```

Running a batch needs an authenticated Apify CLI and can incur external cost. A normal run accepts reviewed `pending` URLs, but refuses previously `ingested` URLs, a page-count mismatch, failed/over-budget results, or unexpected redirects. The remote timeout and fixed page cap are the hard safeguards; the configured dollar amount is a preflight/after-run guard, not an Apify platform hard cap for this Actor.

## Pilot result

Run `uciKhdZjhHKjs0ytM` completed on 2026-09-01 with 12 pages in 121 seconds for `$0.0558161734`. It added 8 OIC pages, 3 Option Alpha course landing pages, and 1 CME course page. Three Option Alpha pages have less than 500 characters of extracted material and are marked `requires_manual_review` rather than treated as high-quality course content.

## Next crawl stage

1. Review short Option Alpha landing-page records and identify deeper public lesson pages, if permitted.
2. Review the pending candidates in `knowledge/url-candidates.json` and approve one small follow-up batch.
3. Add a strategy extractor for OIC strategy pages and a glossary extractor for OIC/Cboe terms.
4. Resolve Cboe's `/en/optionsinstitute/` canonical-path policy before expanding that source.
