# 跑通

```bash
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
```

没有模型时，研究和价值弃权，简报仍然写出走势、合成和结构菜单。有 `DEEPSEEK_API_KEY` 时去掉 `--no-llm`。富途 OpenD 在 `127.0.0.1:11111` 时，报价和期权链走富途；报价失败按 Futu → FMP → Nasdaq 降级，期权链失败降级 Cboe 延迟链。期权链的 spot 统一使用价格级联选出的 spot。宏观数据走 Supabase 共享层（`macro_latest` 视图），每日 09:30 由 launchd 定时刷新（`com.mioption.macro-refresh`），不随标的请求重复取 FRED。
