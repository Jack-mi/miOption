# miOption

对一只美股做投研，写出不下单的简报。默认标的是 `US.AAPL`。港股仅放行 `HK.03690`、`HK.09992` 两只，其余港股仍拒绝。

```bash
python -m signal_chain.orchestrator --tickers US.AAPL
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
python -m signal_chain.orchestrator --tickers US.AAPL --bias bull --shares 100
python -m signal_chain.orchestrator --tickers HK.03690,HK.09992
```

顺序是：数据层取数，三份信号，规则合成，27 个结构过风控，中文简报。模型走 Claude Agent SDK，只请求 DeepSeek 官方的 `deepseek-flash`。密钥在仓库根目录 `.env` 的 `DEEPSEEK_API_KEY`。

`--bias` 和 `--shares` 只重筛结构菜单。三份信号的方向不改。

27 张策略笔记在 `knowledge/wiki/strategies/`。菜单在每条结构后面附一句用途说明，不改过闸结果。

第二条 path：先在全市场筛出候选，再把代码喂回上面那条单股链路（只读，不下单）。

```bash
runtime/.venv/bin/python -m signal_chain.options.screener_bridge seller US 20   # 期权卖方专区
runtime/.venv/bin/python -m signal_chain.options.screener_bridge earnings US 20 # 财报期权筛选
runtime/.venv/bin/python -m signal_chain.options.screener_bridge rating 20      # 美股评级变动
# 其余 screen: rank / movers / hot
python -m signal_chain.orchestrator --tickers US.NKE,US.SOXL
```

输出单行 JSON，`candidates` 就是喂给 `--tickers` 的标的池。

测试分两套 venv，别混：

```bash
./.venv-sc/bin/python -m pytest signal_chain/tests -q            # 156 passed（根目录跑）
cd runtime && ./.venv/bin/python -m pytest tests -q              # 51 passed（runtime 里跑）
```

架构见 [docs/architecture.md](docs/architecture.md)。
