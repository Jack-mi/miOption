# miOption 期权知识库当前状态

更新时间：2026-09-01

## 一、当前结论

项目已从“小样本探测”进入“受控小批量验证”阶段，但尚未开始批量建设或结构化知识抽取。

已验证链路：

1. 使用 Apify Actor `apify/website-content-crawler` 抓取固定 URL 批次。
2. 使用 Apify CLI 下载 dataset。
3. 将页面规范化为本地 JSON + Markdown。
4. 生成/合并 `knowledge/index.json` 文档索引。
5. 将来源 host/path 白名单、页数、状态、HTTP 状态、内容长度与实际成本校验放在入库前。

当前索引共有 16 条文档：OIC 9、Cboe 1、Option Alpha 4、CME 2。Investopedia 明确排除，原因是其 robots 和条款禁止自动化抓取、构建数据集及 AI/RAG 用途；只保留人工整理的概念索引和外部链接，不存正文。

## 二、已完成的运行

| 批次 | Run ID | 结果 | 页数 | 成本 |
|---|---|---:|---:|---:|
| 初始小样本 | `eFrLt82BtQqJZQQXV` | `SUCCEEDED` | 4 | `$0.0458169692` |
| 固定 URL pilot | `uciKhdZjhHKjs0ytM` | `SUCCEEDED` | 12 | `$0.0558161734` |
| 意外重复 run（已强制终止） | `BJvDpPGhHnHlwSM1I` | `ABORTED` | 1/12 | `$0.0043485752` |

受控 pilot 使用 12 个已审核候选 URL，深度 `0`、单并发、单次重试、启用 robots.txt、不用 sitemap 或链接发现，并将远端 timeout 限为 300 秒。它运行 121.442 秒，所有 12 条结果均为批准来源、路径匹配、HTTP 200。

本次新增的 pilot 与已终止重复 run 合计成本为 `$0.0601647486`，低于用户授权的 `$1`；连同此前小样本，当前已记录 run 的总成本为 `$0.1059817178`。没有继续启动后续批次。

## 三、当前项目产物

### 配置与说明

- `README.md`：项目说明、验证方式、pilot 结果和下一阶段。
- `sources.json`：来源、路径 allowlist、页面/超时/质量和成本防护策略。
- `knowledge/url-candidates.json` 与 `.csv`：候选 URL、主题、优先级、审核状态、批次和备注。
- `STATUS.md`：当前状态与待办。

### 脚本

- `scripts/probe.py`：固定 URL 批次的抓取与入库脚本。

当前能力：

- 生成 Apify Actor 输入并可用 `--print-input` 做无费用预检。
- 拒绝非 HTTPS、未知 host、未允许 path、深度非 0、页数不匹配或预估成本超额的批次。
- 传递 `includeUrlGlobs`、robots.txt、并发、重试和远端 timeout。
- 当本地等待失败时尝试强制终止仍在运行的远端 run。
- 校验完成状态、退出码、实际成本、结果页数、HTTP 状态、最终 URL 和内容长度后，才写页面/索引。
- 为短内容记录标记 `quality.requires_manual_review`。
- 支持 `--run-id` 复用已完成的、输入策略匹配的 run；普通新 run 会拒绝索引中已有的 URL，避免重复计费。

自检命令：

```bash
python3 scripts/probe.py --check
```

### 数据与安全

- `data/raw/pages/`：16 个页面的结构化 JSON 和 Markdown，共 32 个文件。
- `knowledge/index.json`：16 条文档索引。
- `data/run-summaries/`：提交不含签名 URL 或密钥的运行摘要。
- `data/raw/runs/`：本地完整运行元数据，始终由 `.gitignore` 排除。

完整 Apify run 元数据曾包含运行时签名材料与带签名 URL，因此不得提交；历史完整原始文件仍只在本地、已被 Git 忽略。若它曾被仓库外分享，应按凭据暴露处理并在 Apify 侧轮换/失效相关访问能力。

## 四、数据质量结果

pilot 新增：OIC 8 页、Option Alpha 3 页、CME 1 页。

OIC 和 CME 的新增页面正文长度为约 799–5,468 字符。下列 Option Alpha 课程入口页内容较薄，已入库为可追溯入口，但必须人工复核，不能直接作为高质量课程正文：

| URL | 内容字符数 |
|---|---:|
| `https://optionalpha.com/courses/options-basics` | 179 |
| `https://optionalpha.com/courses/pricing-volatility` | 461 |
| `https://optionalpha.com/courses/options-expiration` | 188 |

## 五、已确认的抓取范围

### OIC

公开 sitemap 当前可提取 106 个核心 allowlist URL（`/optionsoverview/`、`/strategies/`、`/advancedconcepts/`、`/referencelibrary/`）。当前已抓取基础、定价、行权、风险和四项 Greeks；策略页留待结构化抽取设计完成后再分批审核。

### Option Alpha

公开 sitemap 当前可提取 17 个教育/课程/策略/handbook allowlist URL。课程入口中存在内容较薄的页面，需要先做人工质量筛选，再决定是否深入其公开子页面。

### Cboe

已保留 1 个成功样本。其入口发现的部分链接直连为 403，且 canonical 路径可能落在 `/en/optionsinstitute/`，与当前 `/optionsinstitute/` 白名单不一致；在修订来源策略并重新验证前不扩展。

### CME

已保留课程入口和 `Introduction to Options` 两页。后续仅从已审核课程入口建立固定 URL 批次，不使用站内深度发现。

## 六、当前 Todo

### P0：已完成

1. 建立候选 URL 清单和分类字段。
2. 将来源 host/path allowlist 实际传给 Actor 并在本地 fail-closed 校验。
3. 固定批次上限、预估成本、远端 timeout、状态/结果校验和短内容复核标记。
4. 添加 `.gitignore`，排除 Python 缓存、环境文件和完整 run 元数据。
5. 完成首次提交项目骨架（待本轮最终验证后执行）。

### P1：下一批前的人工决策

1. 审核 3 个 Option Alpha 短内容入口页，确认是否应保留、替换或仅作链接目录。
2. 审核 `knowledge/url-candidates.json` 中 `pending` 的下一批候选（包含策略和 CME Greeks）；已完成的 pilot-12 记录已标为 `ingested`，普通新 run 会拒绝重跑。
3. 明确 Cboe `/en/optionsinstitute/` 是否可加入白名单。
4. 每批保持固定 URL、深度 0，并复核实际成本后再批准下一批。

### P2：结构化抽取

1. 从 OIC 策略页提取结构化策略数据。
2. 从 OIC 和 Cboe 提取术语表。
3. 从 OIC Advanced Concepts 提取 Greeks 知识。
4. 从 CME 提取期货期权差异、保证金和结算知识。
5. 生成课程路径和依赖关系。

### P3：面向自动交易系统

1. 将策略库转换为机器可读模板。
2. 为策略加入生命周期状态机。
3. 建立交易前检查清单、持仓监控、调整规则与风险/禁用条件引擎。

## 七、风险与注意事项

1. 不做整站抓取；仅允许固定、审核后的 URL 批次。
2. 不抓取 Investopedia。
3. Apify 该 Actor 的计费模型不提供可验证的美元硬封顶；真正的硬防线是页数、深度、并发和远端 timeout，成本阈值只用于发起前和完成后的拒收校验。
4. 原始 run 元数据可能含签名 URL/运行时密钥，禁止提交。
5. 版权与使用边界：保留来源、URL 和用途说明，避免将商业内容重新发布为自有数据。
6. 先审质量、再扩量；短页面和课程目录不能直接当作可用知识正文。
