# 上游依赖接触面清单（升级时必查）

锁版本见 `vendor.lock.json`；升级走 `scripts/upstream_check.py` 演练流程。**永不自动升级。**

| 依赖 | 我们依赖的具体接口 | 风险 | 守门测试 |
|---|---|---|---|
| TradingAgents (vendor @ lock) | `propagate(ticker, date)` 返回 `(final_state, rating)`；`save_reports()`；`TRADINGAGENTS_*` 环境变量；五档评级字符串 Buy/Overweight/Hold/Underweight/Sell/REVIEW；`openai_client.py` provider 注册表（受管 patch 落点 `TRADINGAGENTS_FORCE_RESPONSES_API`） | 中 | `tests/contracts/test_ta_contract.py` |
| DSA (vendor @ lock) | `main.py --stocks <codes>` CLI；`hk00700` 代码格式；`reports/report_YYYYMMDD.md` 产出位置与"评分/操作"字段；`LLM_{CHANNEL}_*` 渠道变量（含 `API_SURFACE=responses`）；Futu OpenD 配置 | 中 | `tests/contracts/test_dsa_contract.py` |
| aihf（未安装，M5） | CLI JSON stdout schema；mandate YAML schema | 低 | M5 时补 |
| yfinance（.venv-sc 钉版） | `Ticker.options`、`option_chain()` 列名（contractSymbol/strike/bid/ask/lastPrice/impliedVolatility/openInterest/volume） | 中 | 运行时 ChainSnapshot 校验 + 降级标记 |
| openai-codex SDK（.venv-sc 钉版） | `AsyncCodex.thread_start(model, sandbox)`、`thread.run(prompt, output_schema)`、`TurnResult.final_response`、`Sandbox.read_only` | 低 | M2 E2E |
| 本机 8790 路由 | `POST /v1/responses` 免鉴权可用（2026-09-23 实测）；chat/completions 不可用 | 中（本机服务，漂移自担） | `scripts/upstream_check.py --probe` |
| 8799 翻译 shim（自有组件） | `POST /v1/chat/completions` -> 8790 responses 双向翻译；v1 不支持 stream/tools | 低 | shim 单测 + DSA E2E |
| Futu OpenD (11111) | `get_option_expiration_date` / `get_option_chain` / `get_market_snapshot`（含 option_implied_volatility / option_open_interest） | 中 | M3 链快照 fixture |

## 两类漂移

- **代码漂移**（上游发版）：锁版 + 升级演练覆盖。
- **数据源漂移**（Yahoo/东财/Futu 接口变动，不升级也会发生）：运行时 schema 校验 +
  降级路径（美股链 -> yfinance fallback；单引擎失败 -> single_source 降权）+ 简报显式告警。

## 受管 patch

`vendor/patches/tradingagents-responses-custom-baseurl.patch`
放开 TA `openai_client.py` 的 `_is_native_openai_base_url` 限制：env
`TRADINGAGENTS_FORCE_RESPONSES_API=1` 时自定义 base_url 也启用 Responses API。
setup 与升级演练时 `git apply --check` 验证；apply 失败 = 红灯，TA 临时回退直连厂商 key。

## 已知坑（2026-09-23 M0 实记）

1. TA 必须 editable 安装（`uv pip install -e .`）：普通 `pip install .` 会把未打 patch 的副本
   装进 site-packages，运行时静默走 chat/completions 被 8790 打回 502。升级演练重建 venv 同理用 -e。
2. 8790 的 Responses 载荷缺 created_at 等字段：langchain 宽容能过，litellm 严格解析必炸。
   litellm 系组件（DSA）一律走 8799 shim，不要直连 8790，也不要用 DSA 的 API_SURFACE=responses。
3. DSA 首次运行会初始化 sqlite，禁止两个 DSA 进程并发（表结构创建竞争）。orchestrator 逐标的串行。
