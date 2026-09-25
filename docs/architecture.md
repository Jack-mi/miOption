# 一条投研工作流

对一只美股取数、判断、合成、过结构和风控，写出不下单的简报。

1. `signal_chain/data` 取报价、日线、资金、财务、新闻、社交、宏观和期权链。
2. `signal_chain/decision` 与 `signal_chain/research` 写出走势、研究、价值。走势是规则。研究和价值在有密钥时调用模型。
3. `signal_chain/synth` 合成方向。弃权票不投票。合成不改写三份信号。
4. `signal_chain/options` 用合成方向筛 27 个结构。`--bias` 和 `--shares` 只在这一步重筛。说明来自 `knowledge/wiki/strategies/`。
5. `signal_chain/risk` 检查流动性、财报窗口和单笔亏损。然后写简报。

模型是 DeepSeek 官方 `deepseek-flash`，经 Claude Agent SDK 发出。工人没有取数和下单工具。
