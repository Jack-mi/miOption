---
type: overview
title: Vault Overview
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - overview
---

# Vault Overview

This vault is the miOption options knowledge base. URLs and raw pages are evidence, not the product.

## Scope

- Include option concepts, pricing, price-sensitivity measures, lifecycle, strategies, and option-focused courses.
- Include options on futures when the material is about option contracts and their risk or pricing.
- Exclude standalone futures education, videos, webinars, course catalogs, and marketing pages from usable knowledge.
- Do not add stock-picking or timing calls as named strategy cards.
- Crawl education text only. CME Institute and Cboe Options Institute pages are not live market data. See [[Source roles]].

## Layers

1. Crawl evidence stays in `data/raw/pages/` (outside the vault).
2. Immutable copies used by vault skills live in `.raw/captured/`.
3. Source notes, concepts, and strategy entities live in `wiki/`.

Product capability (knowledge Q&A vs market data vs builder/bot) is drawn on `wiki/canvases/product-stack.canvas`. [[Product patterns]] is a UI spec, not a strategy card.

- Source notes: 70
- Concept notes: 13
- Strategy entities: 27
- Published relations migrated as wikilinks: 5

See [[index]], [[Futu strategy coverage]], [[Source roles]], and [[log]].
