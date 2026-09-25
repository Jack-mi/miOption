# signal_chain 迭代验收清单

更新：2026-09-23。范围是美/港单标的、日级期权**决策支持**；不新增自动下单。架构与命令见 [README](README.md)，上游锁版和受管 patch 见 [UPSTREAM](UPSTREAM.md)，工作台独立验收见 [端到端说明](../docs/end-to-end.md)。勾选只表示有测试和真实产物可复核，不能以进程退出码代替数据质量验收。

## 0. 当前基线与待修问题

- [x] TA/DSA 子进程、Codex 合成、Futu 期权链与 IV、确定性风控、中文报告已接线；版本见 [`vendor.lock.json`](../vendor.lock.json)，模型/路由见 [`config.yaml`](config.yaml)。
- [ ] **数据质量不得误判为成功。** `runs/2026-09-23.json`（本地忽略，不入库）曾将 DSA AAPL 标为 `ok=true`，但同日 DSA 报告写明行情、日线、技术、筹码、基本面、新闻缺失、质量 38/100；TA AAPL/HK 虽有 `rating`，还需逐字段验证价格/财报/日期/来源。历史报告不能证明当前可用。
- [ ] **信号合成先治理缺数。** 当前适配器主要从 DSA 的评分/操作与 TA 的评级抽方向；补齐质量标记、时间戳和可验证证据后，缺关键行情/日线的信号不得被当成完整第二票；`single_source`/`conflicted` 降级应显式传至报告和风险闸。见 [`adapters/`](adapters/)、[`synth/combine.py`](synth/combine.py)。
- [ ] **策略结构校验失败。** AAPL 一次长跑中 strategy 两次输出未通过 `StrategyResult`（缺 `name`/`thesis`/`legs`），导致无结构；检查输出 schema、提示词与模型 JSON 兼容性，失败时明确标记不交易，不拿空列表冒充无机会。见 [`pipeline/steps.py`](pipeline/steps.py) 和 [`agents/prompts.py`](agents/prompts.py)。

## 1. 确定性数据层（优先做）

- [ ] 以 AAPL、HK.00700 为样本，先在同一运行日、同一标的记录 TA/DSA 每项实际输入与来源：报价/复权日线/技术指标、财报/公司行动、新闻、资金流、期权链；按 `available / missing / unsupported / stale` 标注，记录 fetch 时间、交易日、时区、错误和数据权限；禁止用 LLM 填空。
- [ ] **验证富途权限后接报价/日线。** OpenD SDK 有 `get_market_snapshot`、`request_history_kline`、`get_cur_kline`；先用只读请求实测 AAPL 和 HK.00700 的订阅/历史额度、分页、复权、交易日与延迟。能取到的价格和日线可复用到 TA/DSA 共用的标准化快照；失败保留 Yahoo/原有源降级，并显式记录来源和失败原因。现有期权链桥只覆盖链，**不等于**引擎的股票数据已由富途提供。见 [`options/futu_bridge.py`](options/futu_bridge.py)。
- [ ] **资金面逐项验证。** 富途 SDK 暴露 `get_capital_flow`，验证 US/HK 标的权限、统计口径、历史窗口和返回完整度；成交量/成交额不冒称“主力资金净流入”；不可得的港股通、机构持仓等字段保持 unsupported，不推断。
- [ ] **基本面与新闻保持独立来源。** 逐字段检查富途可返回的基本资料与财务数据及权限；不要把 `get_market_snapshot` 当作完整三表/公告。不能覆盖的报表/披露以原数据源或权威披露补齐，保存报表期间、披露时间和出处；财经新闻同理，缺失即标记。Yahoo/东财被限流应有上限重试和可观察告警。
- [ ] 抽取 `UnderlyingSnapshot`（或等价最小数据契约）供引擎适配：每字段附 `source / as_of / fetched_at / status`，只在契约层做数值与时效校验；日级快照不得混入盘中旧价，港币/美元不得混算。复用现有 [`schema/`](schema/) / [`options/`](options/) 模式，避免另造全量数据平台。
- [ ] **最小侵入注入。** 不直接改 vendor 工作树的业务代码；先调研 TA dataflows 路由和 DSA provider 扩展点，能在自有 adapter 注入标准化快照就不打补丁；如必须 patch，纳入 lock、契约测试和升级演练。现有 TA Responses patch 不代表已解决 Yahoo 取数。见 [上游守门](UPSTREAM.md)。

## 2. 信号、结构、风险

- [ ] 适配器只在“必要数据齐全 + 时间可对齐”时给可行动方向；`ok=true` 且报告为“数据缺失，观望/持有”时应判 `insufficient_data`，不得把 50 分中性票当作独立验证。同步把缺失字段、来源与时效写入 `EngineSignal`、run ledger 和简报。
- [ ] 两源同向、相反、单源、旧源和双源均缺数据分别测；质量权重/弃权规则确定性计算，LLM 仅写说明；无可信数据时不生成可通过风控的交易结构。
- [ ] 期权链保留 Futu 主源、美股 yfinance 降级；结构只能引用真实链上到期日/行权价/合约代码，风控逐腿检查报价、OI、价差、财报窗口和同币种最大亏损。账户权益取不到时必须显式告警并定义是否禁止“通过”，不能静默放行。
- [ ] 策略输出使用可验证的 2–3 候选或明确拒绝理由；JSON/schema 回归覆盖模型失败、缺字段、虚构合约和重试耗尽；最终简报区分“信号不足”“无可用链”“结构校验失败”“风险否决”。

## 3. 验收与持续升级

- [ ] M0：OpenD + Friday 8790/8799 在线时实测 AAPL/HK.00700，保留**脱敏**输入/输出和权限诊断；不把现有 `runs/` 里的短 state/报告当作真实数据的 golden fixture。
- [ ] M1：真实样本转 golden-file 契约，另加权限不足、Yahoo/东财限流、缺字段、过期、币种错误、DSA exit 0 但缺数据等负例；自有代码的离线单测不依赖公网和 OpenD。
- [ ] M2：两源合成与链/策略/风控 E2E 在美股和港股各跑通一次；逐一核对模型、路由、快照时间、标的和账本/报告一致性；失败不掩盖为成功。
- [ ] M3：watchlist ≤5 干跑、人工审阅报告与数据出处；确认只读、无下单路径。调度（港/美收盘后）和 aihf 离线回测等数据质量通过后再启用。
- [ ] 上游月度检查只读；升级时按 [`UPSTREAM.md`](UPSTREAM.md) 与 [`scripts/upstream_check.py`](../scripts/upstream_check.py) 重建隔离环境、重应用 TA patch、跑探针/契约/E2E，全部通过才更新 [`vendor.lock.json`](../vendor.lock.json)；数据源漂移不等于代码版本漂移。

## 4. 数据层缺口收口（2026-09-24）

- [x] EDGAR 联系人已写入 gitignore 的 `signal_chain/.env.data`，不入库。
- [x] Reddit 不申请。美股社交用 StockTwits，港股社交不支持。
- [x] Polymarket 只认 `data/events.json`。空文件跳过，不按公司名搜索。赔率不进决策。
- [x] 账户权益只读富途真实账户（美股 `usd_assets`，港股 `hkd_assets`）。失败只告警，并跳过敞口上限。
- [x] 美股资金流只有富途 `in_flow`。没有则缺失。东财不补美股，成交额不当净流入。
- [x] 港股财务仍要 Yahoo 与东财两个营收相差在 1% 以内才标可用。单源留在 `facts`。
- [x] 宏观改走 Alpha Vantage 的联邦基金利率、CPI、失业率。利率失败再用纽约联储。账本不写数值。不再请求 FRED。
- [x] 美股和港股 `earnings_date` 只接受 Yahoo `earningsDate` 的 `YYYY-MM-DD`。EDGAR 申报日只留在来源备注。
- [x] Alpha Vantage 新闻代码用 `ta_format`，港股为 `0700.HK`。

## 5. 数据层尚未接入（2026-09-25）

只登记缺口。补上之后再勾选。现在不改取数。

- [x] 美股商业模式取 10-K Item 1 正文，出处 edgar。护城河和收入结构仍不是字段。港股商业模式仍缺失。
- [ ] 竞争没有行业、对手、份额字段。投研竞争包仍写缺失。
- [x] 美股风险取 10-K Item 1A 和委托书治理段。港股风险仍缺失。这些正文不借给财务工人，宏观也不借。
- [x] ROE、自由现金流、利息覆盖：两源相差在 1% 以内才写入 `ratios`。对不上的单源留在 `facts`。
- [x] 没有 Reddit 官方凭据时读 Arctic Shift。帖子超过 14 天标 stale，不进社交条目。有官方凭据仍走官方接口。
- [ ] 港股社交不支持。没有免登录的开源接口。
- [ ] Polymarket 在 `events.json` 没有标的映射时跳过。赔率不进决策。补上映射后事件一节才有赔率。
- [ ] 美股资金流只有富途 `in_flow`。13F、内部人交易和做空量都不是净流入。
- [ ] 港股期权链仍只有富途。2026-09-25 核对港交所公开页面，没有返回带买卖价和持仓量的链。Yahoo 不兜港股。
- [x] 宏观三项写入证据摘要。财务切片和风险包仍不读宏观。
- [ ] 单源财务凑不齐两源 1% 时不标可用，数字留在 `facts`。EDGAR 申报日只留在来源备注，不当财报日。

## 完成判定

每个市场至少一只标的以**真实且可追溯的**数据完成“报价与技术 → 基本面/资金面覆盖及缺口声明 → 双引擎合成 → 真实期权链 → 合法候选或明确拒绝 → 风控 → 中文简报”；每一段有时点、来源、失败状态和可重放的脱敏 fixture。仅进程成功、模型有回答或报告看起来合理，都不算完成。
