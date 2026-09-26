"""signal_chain - 美港股期权分析决策链（Claude Agent SDK 编排）。

分层：信号引擎 -> 抽取/合成（Claude Agent SDK，请求 DeepSeek）-> 期权链 -> 策略 -> 风控闸 -> 简报。
原则：LLM 只做理解/抽取/合成/表达；取数、校验、风控、落盘全是确定性代码。
"""

__version__ = "0.1.0"
