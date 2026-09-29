# miOption runtime

`runtime/.venv` 是**唯一装了 `futu-api` 的解释器**，`signal_chain` 的富途只读桥靠它执行：

```bash
runtime/.venv/bin/python -m signal_chain.options.futu_bridge US.AAPL 60
runtime/.venv/bin/python -m signal_chain.options.underlying_bridge US.AAPL 2026-09-26
runtime/.venv/bin/python -m signal_chain.risk.account_equity_bridge US
```

`signal_chain/config.py:require_runtime_python()` 硬钉这个路径，缺失就报错，不会用当前解释器顶上。
取链需要 OpenD 在线（默认 `127.0.0.1:11111`）。

`seller_scan` 实盘时盘中会先通过 OpenD 只读刷新过期盘口，再调用共用收租评级器。无法取得同一进程内、未过期的 `signal_chain` 决策及复核时，仅出观察卡；不会把历史人工 adopt 当作晋级依据。历史卡、跟踪及人工 verdict 不覆盖；`seller_follow.py --submit` 始终拒绝，不会下单。其他既有交易工具不属于本研究决策链。

本机 MCP 注册在 `~/.cursor/mcp.json` 的 `mioption`（`MIOPTION_FUTU_MOCK=0` 走真实 OpenD，
`MIOPTION_VAULT=knowledge`），入口是 `python -m mioption_runtime.agent.stdio_mcp`。
Codex 宿主的接线样例见 `.codex/config.toml.example`。

依赖和重建方式见 `requirements.txt`：

```bash
cd runtime && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
