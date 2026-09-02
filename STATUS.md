# miOption：当前项目现状

更新时间：2026-09-02
状态：知识库已迁入 claude-obsidian vault（`knowledge/`）。10 张概念笔记 + 21 张 evergreen 策略实体 + 5 条关系 wikilink 已导入；对角策略仍为 developing；无待抓批次。

## 1. 结论

项目已经从“收集网页 URL”转入“构建可引用的期权知识”的阶段。URL 和原始页面只负责提供证据与追溯。**当前知识成品是 Obsidian vault**（`knowledge/wiki/`），不是 JSON 文件。Agent 应使用 wiki / wiki-query，而不是 `items.json`。

当前链路已跑通：

```text
原始期权页面 → 页面准入 → vault `.raw/captured` → wiki 源笔记 / 概念 / 策略实体 → wikilink
```

产品代码在 `vendor/claude-obsidian/`（pin 见 `vendor/claude-obsidian.pin`），与 vault 分离。策略覆盖已对齐**富途官方策略菜单**（自定义除外）：清单用富途，证据用 OIC。vault 内 10 张概念、**22** 张策略实体、5 条关系。除对角策略外均为 evergreen。

## 2. 范围与准入边界

### 收录范围

- 期权基础、定价、Greeks、交易生命周期、风险规则和策略；
- 页面主体是期权的期货期权（options on futures）内容；
- 有独立、可引用文字正文，并能填充明确知识字段的内容。

### 排除范围

- 与期权无实质关联的纯期货教育、交易或产品内容；
- 视频、webinar、podcast、playlist、视频课入口、交互式课程、课程目录、营销/导航页；
- 只有 URL、不能形成可验证知识字段的页面；
- 富途「自定义策略」：产品功能，不做标准策略卡。

课程和视频页可保留在来源目录中作为导航线索，但不会生成 chunk、知识卡、策略卡或进入知识检索。

## 3. 当前数据快照

| 层级 | 数量 | 含义 |
|---|---:|---|
| 原始来源页面 | 39 | 每页保留 JSON 与 Markdown 证据 |
| 正文证据页 | 31 | 满足主题与文字正文准入 |
| 仅目录/课程/视频页 | 8 | 保留来源，不进入知识抽取 |
| 可引用知识片段（chunks，归档 JSON） | 393 | 含标题、行号、内容哈希和来源 URL；不单独做成笔记 |
| vault 源笔记 | 39 | `knowledge/wiki/sources/` |
| vault 概念笔记 | 10 | 概念、定价、Greeks、生命周期、风险、策略原则 |
| vault 策略实体 | 22 | 对齐富途 12 类 + 方向变体；含 Covered Call |
| 有证据的知识关系 | 5 | 已写成笔记间 wikilink（3 条 requires、2 条 affects） |

### 来源构成

| 来源 | 原始页 | 正文证据页 | 仅目录/课程页 |
|---|---:|---:|---:|
| OIC | 30 | 30 | 0 |
| Option Alpha | 5 | 1 | 4 |
| CME | 3 | 0 | 3 |
| Cboe | 1 | 0 | 1 |
| 合计 | 39 | 31 | 8 |

### 富途策略覆盖

详见 [wiki/meta/Futu strategy coverage.md](knowledge/wiki/meta/Futu%20strategy%20coverage.md)。每张策略笔记含含义（腿/目标）、适配场景、做法（最大收益/损失、盈亏平衡、指派或到期），并挂 OIC 段落证据。JSON 快照在 [archive/knowledge-json-2026-09-02/strategy-coverage.json](archive/knowledge-json-2026-09-02/strategy-coverage.json)。

| 富途类别 | 状态 | 策略卡 |
|---|---|---|
| 单腿期权 | ready | Long Call、Long Put、Naked Call、Protective Put |
| 垂直策略 | ready | Bull/Bear Call Spread、Bull/Bear Put Spread |
| 股票担保 | ready | Covered Call（原有）、Cash-Secured Put |
| 领口策略 | ready | Collar |
| 跨式策略 | ready | Long / Short Straddle |
| 宽跨式策略 | ready | Long / Short Strangle |
| 日历策略 | ready | Long Call Calendar |
| 对角策略 | partial | Diagonal 仍为 developing（无独立 OIC 页；盈亏字段暂用日历同名段落） |
| 蝶式策略 | ready | Long Call Butterfly |
| 鹰式策略 | ready | Long Call / Long Put Condor |
| 铁蝶式策略 | ready | Short Iron Butterfly |
| 铁鹰式策略 | ready | Short Condor (Iron Condor) |
| 自定义策略 | 跳过 | 不做卡 |

## 4. 知识库架构

```text
原始证据
  data/raw/pages/<document_id>.json / .md
  data/raw/index.json
        │
        ▼
页面准入（归档）
  archive/knowledge-json-2026-09-02/source-catalog.json
        │
        ▼
vault 不可变源
  knowledge/.raw/captured/<sha256>.md
        │
        ▼
wiki
  knowledge/wiki/sources/
  knowledge/wiki/concepts/
  knowledge/wiki/strategies/
```

真正供后续使用的入口是 vault 笔记。JSON 层保留在 `archive/knowledge-json-2026-09-02/` 供回滚和 `build_knowledge.py --check`。构建脚本允许不同页面出现相同 boilerplate 段落，但同一文档内正文片段仍不得重复。

### 已形成的知识内容

- **概念笔记**：10 张，均为 evergreen。
- **策略实体**：22 张；其中 21 张 evergreen，Diagonal Call Spread 保持 developing。
- **关系**：5 条已写成 wikilink（Gamma↔Delta；Covered Call 与基础/行权/Theta/Vega）。新策略之间的关系尚未补。
- **抽查记录**：代表性卡（Covered Call、Cash-Secured Put、Long Call、Protective Put、Bull Call Spread、Iron Condor、Collar、Long Straddle、Call Calendar、Diagonal）字段与证据引用均通过；全量 22 张策略卡证据链完整。对角策略定义有日历页 Description/Variations 支撑，但 max gain/loss/breakeven 仍是同执行价日历口径，故未升 evergreen。

## 5. 抓取、成本与约束

### 历史运行

| 批次 | Run ID | 结果 | 页面 | 成本 |
|---|---|---:|---:|---:|
| 初始小样本 | `eFrLt82BtQqJZQQXV` | `SUCCEEDED` | 4 | `$0.0458169692` |
| 固定 URL pilot | `uciKhdZjhHKjs0ytM` | `SUCCEEDED` | 12 | `$0.0558161734` |
| 重复运行（已终止） | `BJvDpPGhHnHlwSM1I` | `ABORTED` | 1 / 12 | `$0.0043485752` |
| 三页跟进批次 | `z89ZwcnZUNwpJf6QA` | `SUCCEEDED` | 3 | `$0.0155027516` |
| 富途策略 A | `gu9ldfoHnNp8ctld9` | `SUCCEEDED` | 12 | `$0.0565566491` |
| 富途策略 B | `PUZYbnrk9cH2qOIMW` | `SUCCEEDED` | 8 | `$0.0315424827` |

- 已记录总成本：约 `$0.2095836011`。
- `$1` 探索额度中（pilot + 终止跑 + followup + A + B）累计约 `$0.1637666320`，约余 `$0.836`。
- 候选队列 35 个 URL 均为 `ingested`；没有 `approved` 待抓批次。
- 另有 4 篇初始小样本页面不在候选队列中且缺 `run_id`（legacy）。

### 实际采集护栏

`scripts/probe.py` 只允许固定且审核过的 URL 批次：HTTPS、来源和路径白名单、深度 `0`、robots.txt、单并发、单次重试、远端 300 秒超时，以及结果数量、HTTP 状态、内容长度和成本校验。新抓取必须走 `approved` 候选，不能直接传 URL。

## 6. 关键文件索引

| 文件 | 作用 |
|---|---|
| [README.md](README.md) | 项目总览 |
| [STATUS.md](STATUS.md) | 本文件 |
| [sources.json](sources.json) | 白名单与运行限制 |
| [data/pipeline/url-candidates.json](data/pipeline/url-candidates.json) / [.csv](data/pipeline/url-candidates.csv) | 候选队列 |
| [knowledge/](knowledge/) | Obsidian vault（知识成品） |
| [knowledge/wiki/meta/Futu strategy coverage.md](knowledge/wiki/meta/Futu%20strategy%20coverage.md) | 富途清单 ↔ 策略笔记 |
| [archive/knowledge-json-2026-09-02/](archive/knowledge-json-2026-09-02/) | 迁移前 JSON 快照 |
| [vendor/claude-obsidian/](vendor/claude-obsidian/) | 知识库运行时（技能/CLI） |
| [scripts/probe.py](scripts/probe.py) | 抓取（默认索引 `data/raw/index.json`） |
| [scripts/build_knowledge.py](scripts/build_knowledge.py) | 重建归档 JSON |
| [scripts/export_vault_notes.py](scripts/export_vault_notes.py) | JSON → vault Markdown |

## 7. 已验证项与已知缺口

```bash
python3 -m py_compile scripts/probe.py scripts/build_knowledge.py scripts/export_vault_notes.py
python3 scripts/probe.py --check
python3 scripts/build_knowledge.py --check
python3 vendor/claude-obsidian/scripts/claude-obsidian.py doctor --vault knowledge
python3 vendor/claude-obsidian/scripts/claude-obsidian.py lint --vault knowledge --as-of 2026-09-02
```

当前 `build_knowledge.py --check` 预期：

```json
{"ok": true, "chunks": 393, "items": 10, "strategies": 22, "relations": 5}
```

已知缺口：

- Diagonal Call Spread 仍为 developing：需独立对角文字页，或按对角口径改写盈亏字段后再升 evergreen。
- 新策略卡之间尚未补 requires / related_to 等关系。
- taxonomy 的 `options_on_futures` 仍为空；流动性、保证金、期货期权结算仍未做。
- 短 chunk 与 taxonomy 100 字门槛仍未强制对齐（可选后续处理）。
- Cboe canonical `/en/optionsinstitute/` 路径策略未定。

## 8. 下一步待办

1. 对角策略：找独立文字证据页，或收窄字段只保留有对角原文支撑的含义/场景后再发布。
2. 按需补策略关系（例如垂直四向互为 `related_to`，铁鹰依赖垂直概念）。
3. 流动性、保证金、期货期权结算等专题另开缺口后再批候选。
4. 不做整站抓取；Investopedia 仍不自动采。

## 9. 交接注意事项

- 不做整站抓取，不绕过 robots；Investopedia 明确不做自动采集。
- 原始页面是带版权约束的证据材料，不重新发布为自有内容。
- 完整 Apify 运行元数据在 `data/raw/runs/`（Git 忽略）；仓库内为脱敏 `data/run-summaries/`。
- 产品仓库 `vendor/claude-obsidian` 不是 vault；不要往里面写知识。
- 工作区含大量未提交的知识层与新原始页；不要用 `reset` / `checkout` 丢弃。
