# miOption options knowledge base

This project builds a source-backed local knowledge base for options education and strategy research. Broker/bot/agent runtime (Futu OpenD bridge, default SIMULATE/mock) lives under [`runtime/`](runtime/) and is separate from the crawl pipeline. URLs are evidence locations, not the knowledge product. The live knowledge layer is an [Obsidian](https://obsidian.md) vault at [`knowledge/`](knowledge/), operated with [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian).

## Scope

- Include option concepts, pricing, price-sensitivity measures (Delta, Gamma, Theta, Vega), lifecycle, strategies, and option-focused courses.
- Include options on futures when the material is about option contracts and their risk or pricing.
- Exclude standalone futures education and other material that is not materially about options.
- Exclude videos, webinars, course catalogs, interactive course pages, and marketing/landing pages from the usable knowledge corpus.

## Current status

See [STATUS.md](STATUS.md) for the live snapshot, known gaps, and sequenced to-dos.

- The raw evidence layer has 72 normalized source documents; 64 substantive text pages are eligible, while 8 video/course/catalog pages are retained only as navigation metadata.
- The vault contains 70 source notes, 13 concept notes, 27 evergreen strategy entities, and five relations as wikilinks. Coverage is one set: Futu App menu ∪ topic474.
- There is no `approved` crawl batch. `new-topics-1usd` is ingested (`dwOriSJHmglF1wbJA`, ~$0.004). Two OIC URLs remain `proposed` as `futu-topic474-gaps`.
- Crawl scope is enforced in code: HTTPS-only source/path allowlists, fixed URL batches, depth `0`, robots.txt checks, and post-run validation of page count, status, source path, and cost.
- Investopedia is excluded from automated crawling because its robots/terms prohibit automated scraping and AI dataset use.
- Complete Apify run metadata is local-only and ignored by Git because it can contain signed URLs and runtime secrets. The repository contains only sanitized run summaries.

## Run the local research workbench

From the repository root, after the runtime setup in `runtime/README.md`:

```bash
runtime/.venv/bin/python runtime/scripts/serve_h5.py --mode mock --chat
```

Open `http://127.0.0.1:8765/chain.html`, `desk.html`, or `chat.html`. Mock prices are explicitly labeled and stored separately. For real market data, start and login to Futu OpenD, then replace `--mode mock` with `--mode live`. Chat requires an authenticated OpenCode provider; omit `--chat` to run the market/research pages alone. Use `--model provider/model` to select another configured model.

The browser/chat path is research-only: it cannot place orders or run order automations. Live means real market data, not permission to trade. Freshness, source separation, scan/adopt/dry-run/monitor/reload, and expired-card review are covered by the runtime tests. See `docs/end-to-end.md` for acceptance evidence and the manual checks.

## Layout

- `sources.json` — source policy, limits, and source/path allowlists
- `data/pipeline/url-candidates.json` / `.csv` — reviewed crawl candidates (`ingested` pages cannot be re-run normally)
- `scripts/probe.py` — bounded Apify crawl runner
- `data/raw/pages/` — crawl authority: normalized public page records
- `data/raw/index.json` — generated document index
- `data/run-summaries/` — committed sanitized run summaries
- `data/raw/runs/` — ignored local-only complete run metadata
- `knowledge/` — Obsidian vault (wiki notes, `.raw/captured/`, inbox)
- `vendor/claude-obsidian/` — pinned claude-obsidian product (CLI and skills)
- `archive/knowledge-json-2026-09-02/` — frozen JSON snapshot of the pre-vault knowledge layer
- `scripts/build_knowledge.py` — rebuilds the archived JSON layer from raw pages
- `scripts/export_vault_notes.py` — exports that JSON snapshot into vault Markdown

## Use the vault

```bash
python3 scripts/probe.py --check
python3 scripts/build_knowledge.py --check
python3 vendor/claude-obsidian/scripts/claude-obsidian.py doctor --vault knowledge
python3 vendor/claude-obsidian/scripts/claude-obsidian.py lint --vault knowledge --as-of 2026-09-20
```

Agents should read `knowledge/wiki/` (index, concepts, strategies, sources) and query through claude-obsidian skills (`wiki`, `wiki-query`, `wiki-ingest`). Cursor skill links live in `.cursor/skills/` and point at `vendor/claude-obsidian/skills/`. Do not treat `items.json` as the live product.

The crawler is only an evidence acquisition tool: a new crawl requires an `approved` candidate batch that declares a knowledge target, expected fields, textual content kind, and `video: false`. Direct URL crawling is blocked. After capture, copy Markdown into the vault with `scripts/export_vault_notes.py` or claude-obsidian `wiki-ingest`. `data/raw/pages` remains the crawl original; `.raw/captured/` is the vault-local immutable copy.

## Completed runs

| Run | Pages | Cost | Result |
|---|---:|---:|---|
| `eFrLt82BtQqJZQQXV` | 4 | `$0.0458169692` | Initial smoke test |
| `uciKhdZjhHKjs0ytM` | 12 | `$0.0558161734` | Fixed-URL pilot |
| `z89ZwcnZUNwpJf6QA` | 3 | `$0.0155027516` | Covered call, neutral strategies, and Option Greeks |
| `gu9ldfoHnNp8ctld9` | 12 | `$0.0565566491` | Futu strategy coverage batch A |
| `PUZYbnrk9cH2qOIMW` | 8 | `$0.0315424827` | Futu strategy coverage batch B |
| `dwOriSJHmglF1wbJA` | 4 | `$0.0042865904` | New-topic trial: margin, options on futures, Wikipedia |

Batches A and B added twenty OIC strategy text pages used to build the Futu-aligned strategy cards. CME course pages remain catalog-only; Option Alpha short course landings remain `body_eligible: false`.

## Knowledge architecture

```text
Raw source evidence (data/raw/pages + data/raw/index.json)
  → source catalog admission
  → vault .raw/captured copies
  → wiki/sources, wiki/concepts, wiki/strategies
  → wikilinks and source/claim ledgers
```

The source URL stays attached to each source note for verification. Retrieval should start from vault notes, not from a URL list.

## Next knowledge stage

Full sequence is in [STATUS.md](STATUS.md). In short:

1. Merged coverage is in [wiki/meta/Futu strategy coverage.md](knowledge/wiki/meta/Futu%20strategy%20coverage.md). Put butterfly / put calendar, Strap / Strip, and Diagonal are evergreen; strap/strip and diagonal publish structure, not a single profit-and-loss formula.
2. Approve `futu-topic474-gaps` if those two OIC pages should land in `data/raw/pages`. Typical option bid-ask width still has no dedicated source.
