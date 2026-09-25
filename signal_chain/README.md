# signal_chain

美股投研工作流。默认 `US.AAPL`。不下单。

```bash
python -m signal_chain.orchestrator --tickers US.AAPL
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
python -m signal_chain.orchestrator --tickers US.AAPL --bias bull --shares 100
```

数据在 `data/`。三份信号在 `decision/` 和 `research/`。合成在 `synth/`。结构和笔记说明在 `options/`。风控在 `risk/`。模型在 `agents/llm.py`，只打 DeepSeek 官方 `deepseek-flash`。

`--bias` 和 `--shares` 只重筛菜单。
