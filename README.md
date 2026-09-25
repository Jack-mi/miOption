# miOption

对一只美股做投研，写出不下单的简报。默认标的是 `US.AAPL`。港股取数代码还在，这次不以港股为跑通标准。

```bash
python -m signal_chain.orchestrator --tickers US.AAPL
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
python -m signal_chain.orchestrator --tickers US.AAPL --bias bull --shares 100
```

顺序是：数据层取数，三份信号，规则合成，27 个结构过风控，中文简报。模型走 Claude Agent SDK，只请求 DeepSeek 官方的 `deepseek-flash`。密钥在仓库根目录 `.env` 的 `DEEPSEEK_API_KEY`。

`--bias` 和 `--shares` 只重筛结构菜单。三份信号的方向不改。

27 张策略笔记在 `knowledge/wiki/strategies/`。菜单在每条结构后面附一句用途说明，不改过闸结果。

架构见 [docs/architecture.md](docs/architecture.md)。
