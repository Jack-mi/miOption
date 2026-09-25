# 现状

项目是一条美股投研工作流，入口是 `python -m signal_chain.orchestrator --tickers US.AAPL`。

数据从自建数据层来。判断是走势、研究、价值三份信号。结构菜单读取 `knowledge/wiki/strategies/` 的一句说明。用户可以用 `--bias` 和 `--shares` 重筛菜单，不改三份信号。

这条链路不下单。港股取数仍在代码里，不作为当前跑通标准。
