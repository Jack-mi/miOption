# signal_chain

美股投研工作流。默认 `US.AAPL`。不下单。

```bash
python -m signal_chain.orchestrator --tickers US.AAPL
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
python -m signal_chain.orchestrator --tickers US.AAPL --bias bull --shares 100
```

数据在 `data/`。三份信号在 `decision/` 和 `research/`。合成在 `synth/`。结构和笔记说明在 `options/`。风控在 `risk/`。模型在 `agents/llm.py`，只打 DeepSeek 官方 `deepseek-flash`。

`--bias` 只影响候选方向；`--shares` 仅作自述展示，不代替真实账户持仓。

收租候选和 `seller_scan` 共用 `runtime/mioption_runtime/seller/income.py`。仅覆盖美股 1x1、标准 100 股合约的有限风险信用价差；卖 bid、买 ask，收益/最大亏损至少 10% 才可能晋级。OI、价差、财报日、连续日线、信号与复核、美元计价的 REAL 账户权益和标的/双腿时间戳须同时过关。配置在 `config.yaml` 的 `risk` 节。

三档为「可考虑」「仅观察」「禁做」；仅在最近一个常规交易日收盘前五分钟的同步报价符合要求时，盘外展示「条件可考虑，开盘须重报价」，不算即时晋级。延迟源、缺数、过期或跨进程缺决策证据最高仅观察。旧卡和人工 verdict 保留原样，重新扫描只重评展示；列表里的旧卡降级展示。review 完成表示既定检查完成，不表示全面交易验证。没有下单路径。
