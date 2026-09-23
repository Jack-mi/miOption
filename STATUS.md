# miOption：当前项目现状

更新时间：2026-09-20
状态：知识库已迁入 claude-obsidian vault（`knowledge/`）。**13** 张概念 + **27** 张策略（全部 evergreen：对角/Strap/Strip 已按 Wikipedia 落地结构；裸卖 put 已补）。App 菜单与 topic474 为一套覆盖。Optionistics Learning Center 续爬已入库（19 课 Source 笔记；转换/合成不建第 28 张策略卡）。

## 2026-09-20 端到端交付

- 本地研究工作台可一条命令启动：`runtime/.venv/bin/python runtime/scripts/serve_h5.py --mode live --chat`。H5 默认 `8765`，OpenCode 默认 `4097`；未占用 Headroom 的 `8787`，不会杀已有监听进程。
- 真实 OpenD 已恢复连接并于本日拉取 BIDU：612 个合约、6 个到期日、564 个有报价、612 个含 Greeks。此为本次拉取快照，不承诺交易所实时流。
- 已在浏览器验证行情展示、知识库 MCP 问答、卖方卡片临时采纳、CLI dry-run、监控保护提醒。未向券商下单；验收临时采纳已清除，验收事件保留并注明用途。
- mock/live 数据分目录。卡片记录来源和拉取时间；过期快照拒绝扫描/标记；重扫保留已采纳卡片、原始权利金及历史；到期只提醒核对，不用当前股价伪造已实现结算。
- 浏览器与 chat 为研究专用，MCP 不暴露下单和订单自动化工具，分发层再次拒绝。CLI 的可选提交能力不属于本轮自动验收范围。
- 回归覆盖 HTTP 拉取→扫描→采纳→dry-run→监控→落盘重读、来源混用、过期、越权访问、MCP 安全模式与启动退出。归档检查已修复为读取匹配的冻结索引，不改写 2026-09-02 快照。
- 完整启动、验收证据与边界见 `docs/end-to-end.md`。以下知识库内容保留作为知识层快照；不再用旧章节判断工作台运行状态。

## 1. 结论

项目已经从“收集网页 URL”转入“构建可引用的期权知识”的阶段。URL 和原始页面只负责提供证据与追溯。**当前知识成品是 Obsidian vault**（`knowledge/wiki/`），不是 JSON 文件。Agent 应使用 wiki / wiki-query，而不是 `items.json`。

当前链路已跑通：

```text
原始期权页面 → 页面准入 → vault `.raw/captured` → wiki 源笔记 / 概念 / 策略实体 → wikilink
```

产品代码在 `vendor/claude-obsidian/`（pin 见 `vendor/claude-obsidian.pin`），与 vault 分离。策略覆盖是**一套**：富途 App 菜单 ∪ [常用期权组合简介](https://support.futunn.com/topic474)。清单用富途；盈亏数字以期权行业协会（OIC）文字为准。对角用 Wikipedia：没有单一盈亏公式。Strap/Strip 用 Wikipedia+Futu 腿结构，不填具体最多赚/亏/打平数字。vault 内 **13** 张概念、**27** 张策略实体、**70** 条源笔记、5 条关系。

## 2. 范围与准入边界

### 收录范围

- 期权基础、定价、价格敏感度（Delta、Gamma、Theta、Vega 等）、交易生命周期、风险规则和策略；
- 页面主体是期权的期货期权（options on futures）内容；
- 有独立、可引用文字正文，并能填充明确知识字段的内容。

### 排除范围

- 与期权无实质关联的纯期货教育、交易或产品内容；
- 视频、webinar、podcast、playlist、视频课入口、交互式课程、课程目录、营销/导航页；
- 只有 URL、不能形成可验证知识字段的页面。

课程和视频页可保留在来源目录中作为导航线索，但不会生成 chunk、知识卡、策略卡或进入知识检索。

### 来源角色（教育 ≠ 行情）

抓取白名单里的网站不是同一类对象。问答 Agent 只用教育证据；行情与交易执行不走 Apify 网页抓取。细则见 vault `wiki/meta/Source roles.md`。

| 角色 | 本仓库怎么用 | 不是什么 |
|---|---|---|
| 教育证据 | OIC 正文为主；Wikipedia 定点补洞；CME Institute **白皮书/有独立文字的教育页**；Optionistics Learning Center 课文（结构可融，盈亏数字仍以 OIC 为准） | 不是期权链、成交明细、隐含波动曲面 |
| 产品形态（设计规格） | OptionStrat 教程、Option Alpha 公开 Bot 结构 → `wiki/meta/Product patterns.md`。不写进 27 张策略卡，不是问答默认路径 | 不是这些网站的数据接口 |
| 禁止当行情源 | CME Market Data API、Cboe DataShop / LiveVol、OptionStrat / Option Alpha / Optionistics Screener 的报价与筛表 | 不得用本仓库爬虫去接 |

CME Institute 教育页 ≠ CME 行情接口。Cboe Options Institute 教育页 ≠ Cboe DataShop。只收有独立文字的 Cboe 教育页；课程目录不再花抓取预算。`/optionsinstitute/` 白名单仍可保留，但目录型 landing 不再批准。

## 3. 当前数据快照

| 层级 | 数量 | 含义 |
|---|---:|---|
| 原始来源页面 | 72 | Apify 抓取（含 new-topics、four-site-match、optionistics-lc） |
| 正文证据页 | 64 | 满足主题与文字正文准入（含 Optionistics 续爬 19 课） |
| 仅目录/课程/视频页 | 8 | 保留来源，不进入知识抽取 |
| vault 本地捕获（未进 raw pages） | 6 | put butterfly/calendar、Futu topic474、Wikipedia 对角/跨式、Naked Put |
| vault 源笔记 | 70 | `knowledge/wiki/sources/`（+19 Optionistics LC） |
| vault 概念笔记 | 13 | 原 10 张 + 保证金、买卖价差、期货期权行权 |
| vault 策略实体 | 27 | 含 Naked Put；对角/Strap/Strip 已按 Wikipedia 落地 |
| 有证据的知识关系 | 5 | 已写成笔记间 wikilink（3 条 requires、2 条 affects） |

### 来源构成

| 来源 | 原始页 | 正文证据页 | 仅目录/课程页 |
|---|---:|---:|---:|
| OIC | 31 | 31 | 0 |
| Option Alpha | 5 | 1 | 4 |
| CME | 4 | 1 | 3 |
| Cboe | 1 | 0 | 1 |
| Wikipedia | 2 | 2 | 0 |
| Optionistics | 23 | 23 | 0 |
| Options Profit Calculator | 3 | 3 | 0 |
| OptionStrat | 2 | 2 | 0 |
| Share Predictions | 1 | 1 | 0 |
| 合计 | 72 | 64 | 8 |

### 富途策略覆盖

详见 [wiki/meta/Futu strategy coverage.md](knowledge/wiki/meta/Futu%20strategy%20coverage.md)。每张策略笔记含含义（腿/目标）、适配场景、做法（最大收益/损失、盈亏平衡、指派或到期），并挂 OIC 段落证据。JSON 快照在 [archive/knowledge-json-2026-09-02/strategy-coverage.json](archive/knowledge-json-2026-09-02/strategy-coverage.json)。

| 富途类别 | 状态 | 策略卡 |
|---|---|---|
| 单腿期权 | ready | Long Call、Long Put、Naked Call、Naked Put、Protective Put |
| 垂直策略 | ready | Bull/Bear Call Spread、Bull/Bear Put Spread |
| 股票担保 | ready | Covered Call（原有）、Cash-Secured Put |
| 领口策略 | ready | Collar |
| 跨式策略 | ready | Long / Short Straddle |
| 宽跨式策略 | ready | Long / Short Strangle |
| 带式 / 条式 | ready | Strap、Strip（腿+方向偏好已发表；无具体最多赚/亏/打平数字） |
| 日历策略 | ready | Long Call Calendar、Long Put Calendar |
| 对角策略 | ready | Diagonal（Wikipedia：无单一盈亏公式；未借用日历数字） |
| 蝶式策略 | ready | Long Call Butterfly、Long Put Butterfly |
| 鹰式策略 | ready | Long Call / Long Put Condor |
| 铁蝶式策略 | ready | Short Iron Butterfly |
| 铁鹰式策略 | ready | Short Condor (Iron Condor) |

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

- **概念笔记**：13 张，均为 evergreen（含保证金、买卖价差、期货期权行权）。
- **策略实体**：27 张，均为 evergreen。对角没有单一盈亏公式；Strap/Strip 不填具体最多赚/亏/打平。
- **关系**：5 条已写成 wikilink（Gamma↔Delta；Covered Call 与基础/行权/Theta/Vega）。另有策略 related（butterfly/calendar/straddle/strap/naked put）。

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
| 新专题 1usd | `dwOriSJHmglF1wbJA` | `SUCCEEDED` | 4 | `$0.0042865904` |
| 四站匹配（合计，见 ledger） | 见 `data/pipeline/apify-smoke-ledger.json` | `SUCCEEDED` | 10 入库 | `~$0.18` of `$5` |
| Optionistics LC-1 | `bYp1NpJN2RsVBHSRf` | salvage 6 / skip 3 short | 9 | `$0.009461` |
| Optionistics LC-2 | `Sgdh96rxVEeKOGf22` | salvage 9 / skip 2 short | 11 | `$0.005709` |
| Optionistics LC-3 | `AWXfMSfWk9gkOdbaT` | salvage 4 / skip 2 short | 6 | `$0.000155` |

- 四站试跑窗 + Optionistics LC 续爬账本 `spent_usd`：`$0.196755`（[`data/pipeline/apify-smoke-ledger.json`](data/pipeline/apify-smoke-ledger.json)）。Cheerio 课页远低于 `$1`/`run`。
- `$1` 探索额度中（pilot + 终止跑 + followup + A + B）累计约 `$0.1637666320`，约余 `$0.836`。
- 候选队列：`optionistics-lc-1`–`3` 已收口（19 ingested / 7 skipped，未降 1200 字门槛）。`four-site-match` 10 页仍 ingested。另有若干 `proposed`（短 `/build` stub、OPC diagonal shell、futu-topic474-gaps）。尚无 `approved` 待抓批次。
- 四站 Actor 赢家与成本账本：[`data/pipeline/apify-actor-matrix.md`](data/pipeline/apify-actor-matrix.md)。`crawl_policy.max_cost_usd` 已从试跑 `$5` 收回 `$1`。Optionistics `include_prefixes` 为 `/s/chapter1`–`/s/chapter5`、`/s/option_spreads`、`/g/`（不抓 TOC `/s/tutorial`）。
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
| [data/pipeline/apify-actor-matrix.md](data/pipeline/apify-actor-matrix.md) | 四站爬虫赢家与 `$5` 试跑账本 |
| [knowledge/](knowledge/) | Obsidian vault（知识成品） |
| [knowledge/wiki/meta/Futu strategy coverage.md](knowledge/wiki/meta/Futu%20strategy%20coverage.md) | 富途清单 ↔ 策略笔记 |
| [knowledge/wiki/meta/Source roles.md](knowledge/wiki/meta/Source%20roles.md) | 教育证据 vs 禁止当行情源 |
| [knowledge/wiki/meta/Product patterns.md](knowledge/wiki/meta/Product%20patterns.md) | Builder / Bot 产品形态规格（非策略证据） |
| [knowledge/wiki/meta/Futu OpenAPI integration.md](knowledge/wiki/meta/Futu%20OpenAPI%20integration.md) | OpenD + futu-api 接入规格（默认 SIMULATE） |
| [runtime/](runtime/) | Bot / Agent / 富途桥接运行时（与抓取隔离；默认 mock）。默认 agent harness 为 Claude Agent SDK；Codex 为可选 overlay。 |
| [docs/futu-api/](docs/futu-api/) | 富途官方 Markdown 文档落点（脚本拉取说明） |
| [knowledge/wiki/canvases/product-stack.canvas](knowledge/wiki/canvases/product-stack.canvas) | 产品能力三层：知识问答 / 行情数据 / Builder+Bot |
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
python3 vendor/claude-obsidian/scripts/claude-obsidian.py lint --vault knowledge --as-of 2026-09-03
```

当前 `build_knowledge.py --check` 预期：

```json
{"ok": true, "chunks": 393, "items": 10, "strategies": 22, "relations": 5}
```

已知缺口：

- Strap / Strip 没有具体最多赚/亏/打平数字（Wikipedia 与 Futu 都没写）。
- Put butterfly / put calendar / Naked Put 的 vault 笔记来自本地捕获，尚未全部经 Apify 写入 `data/raw/pages`。
- taxonomy 的 `options_on_futures` 已有 CME 白皮书笔记；保证金与买卖价差已有概念卡。期权专用流动性宽度（典型 spread）仍没有独立来源。
- 短 chunk 与 taxonomy 100 字门槛仍未强制对齐（可选后续处理）。
- Cboe：课程目录不再抓；仅当存在独立文字/PDF 教育页时再单批审核。DataShop / LiveVol 不走 Apify。
- 归档 JSON（`build_knowledge.py --check`）仍为迁移前 22 张策略，使用归档自己的 39 页索引；vault 已领先。当前 72 页原始索引与冻结归档不应强行对齐。

## 8. 下一步待办

1. 可选：把仍停在本地捕获的 OIC 页（put butterfly / put calendar / Naked Put）批进 `data/raw/pages`。
2. 期权专用流动性（典型买卖价差宽度）还没有独立文字页。
3. Optionistics LC 本轮已完成；转换/合成仅 Source 笔记。不要把 SharePredictions 信号灌进策略卡。OptionStrat `/build/*` stub、OPC www 计算器空壳、Optionistics `/s/tutorial` 目录已标 `skipped`，不再批准为知识抓取。
4. 不做整站抓取；Investopedia 仍不自动采。产品形态见 vault `wiki/meta/Product patterns.md`、`wiki/meta/Futu OpenAPI integration.md` 与 canvas `wiki/canvases/product-stack.canvas`。Bot / 富途运行时在 `runtime/`（默认 `MIOPTION_FUTU_MOCK=1`），不混进 Apify 抓取。本机 OpenD 登录后设 `MIOPTION_FUTU_MOCK=0` 再跑 `runtime/scripts/check_opend.py`。

## 9. 交接注意事项

- 不做整站抓取，不绕过 robots；Investopedia 明确不做自动采集。
- 原始页面是带版权约束的证据材料，不重新发布为自有内容。
- 完整 Apify 运行元数据在 `data/raw/runs/`（Git 忽略）；仓库内为脱敏 `data/run-summaries/`。
- 产品仓库 `vendor/claude-obsidian` 不是 vault；不要往里面写知识。
- 工作区保留已有未提交修改与新增 H5/行情/验收代码；本轮未 commit/push。不要用 `reset` / `checkout` 丢弃。
