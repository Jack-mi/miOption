# Futu OpenAPI docs (local cache)

Download Markdown from the official site (page menu → Download → Markdown) and
unpack here for agent retrieval.

- Portal: https://openapi.futunn.com/futu-api-doc/
- AI onboarding: https://openapi.futunn.com/futu-api-doc/intro/ai.html
- Skills zip: https://openapi.futunn.com/skills/opend-skills.zip

已落地（gitignored，不进版本库）：

- `Futu-API-Doc-zh-Python.md` —— 全量官方文档（Python/中文，约 1 MB，148 个接口，含每个接口的限频与权限说明）。
  刷新：`curl -sL -o docs/futu-api/Futu-API-Doc-zh-Python.md https://openapi.futunn.com/mds/Futu-API-Doc-zh-Python.md`

## 已评估、明确不接入

避免以后重复评估，记下结论和原因：

- `get_dividend_calendar`（全市场派息日历）：按天查，扫一个窗口要 N 次调用；我们只需要手上标的的除息日，用 `get_corporate_actions_dividends` 一次拿到。
- `get_market_state`：闭市判断已由 `signal_chain/sessions.py` 的交易日历/会话对齐解决。
- `get_capital_distribution`（大小单资金分布）：`get_capital_flow` 已在链路上（`underlying_bridge._capital_flow`），它只是更细的粒度，没有缺口，需要时再补。
- `get_valid_combo_list` / `request_combo_quotes`：名字像期权组合，实际是**事件合约（预测市场）的 Combo 询价**，与期权无关。所以 futu 没有多腿组合报价，风控的价差检查只能按单腿算。
- `get_earnings_calendar` / `get_macro_indicator_*` / `get_fed_watch_*`：与仓库已有的 Nasdaq 财报日历、FRED + Supabase 宏观层重复。

Do not commit large generated dumps if they bloat the repo; re-run the site
download or keep them locally gitignored.
