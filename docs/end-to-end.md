# 跑通

```bash
python -m signal_chain.orchestrator --tickers US.AAPL --no-llm
python -m signal_chain.orchestrator --tickers HK.03690,HK.09992 --no-llm
```

没有模型时，研究和价值弃权，简报仍然写出走势、合成和结构菜单。有 `DEEPSEEK_API_KEY` 时去掉 `--no-llm`。富途 OpenD 在 `127.0.0.1:11111` 时，报价和期权链走富途；报价失败按 Futu → FMP → Nasdaq 降级。期权链的 spot 统一使用价格级联选出的 spot。Cboe 自动兜底默认关闭：只有确认程序化使用许可，并在本机显式设置 `MIOPTION_CBOE_PROGRAMMATIC_LICENSE=confirmed`，才可启用延迟链；不因接口可访问而认定获许可。

## 数据链与存储

```text
FRED → 独立每日宏观任务 → Supabase macro_observations / macro_latest / macro_refresh_state ─┐
                                                                                       ├→ 本轮证据包
SEC、Nasdaq、Finnhub → 按需刷新 + 每日观察名单预热 → Supabase underlying_evidence / underlying_refresh ┘
    ↑ 逐字段检查：公司 30 天、财务/申报 7 天、财报日 1 天（临近 10 天每 6 小时）；失败 15 分钟后重试

OpenD 只读报价/期权链/REAL 账户 → 每轮按时间与来源校验 ─┬→ 决策 → 复核 → 简报
Futu 已完成日线 → 本机 daily_bars.sqlite（逐日补取、保留修订） ─┘          └→ Seller 扫描/卡片

本机报价 SQLite / 链 / 报告 / Seller 人工标记 → 本机版本归档；
仅脱敏摘要、路径和元数据进入 Supabase research_archive，旧卡仍只供回放。
```

慢变证据存储来源时点、获取时点、质量与摘要；同一业务键相同内容不重复插入，变更追加版本。读取取当时已经获取的版本，不能用缓存读取时间冒充市场时间。技术指标由已完成日线计算。Futu 报价、期权链和 REAL 账户不上传 Supabase；原始行情远端长期保存须先核实供应商许可。共享库不可用或财务仅有未落库备用源时，允许标注来源继续研究，但收益候选最高「仅观察」。每轮报价、两腿盘口与 REAL 账户仍需各自通过时效闸门；`review` 通过只代表既定检查完成，不是交易保证。

## 运维与恢复

- 项目 `gkchcblxtonfsthfgmbc`；迁移用 `supabase db push --dry-run` 预览、`supabase db push --yes` 执行、`supabase migration list` 核对。仅本机受控进程保管 service role key；新表与宏观视图拒绝匿名及客户端角色读取。
- 本机 launchd：`com.mioption.macro-refresh` 每日 09:30 独立更新共享宏观；`com.mioption.underlying-prewarm` 每日 09:45 只补观察名单慢资料。临时查询的新标的也按需建档。运行 `.venv-sc/bin/python -m signal_chain.data.prewarm --tickers US.AAPL` 可手动只读供应商并刷新共享底座，不读取期权或账户。
- `com.mioption.data-backup` 每日 10:15 调用 `signal_chain/data/backup.sh` 将 `public` 数据导出到 `~/.local/share/mioption/backups`，失败不会留下空文件；可设 `MIOPTION_BACKUP_DIR` 指向受控的异地挂载。当前默认目录仍在本机，**不算异地备份**。如需恢复，先在隔离库核验迁移版本、导出数据与行数，再按审批流程恢复，不直接覆盖生产表。
- 旧产物导入前运行 `.venv-sc/bin/python -m signal_chain.data.archive` 查看清单；`--apply` 保留本地不可变副本并幂等上传脱敏索引。`legacy_unverified`、mock 和无来源时点记录永远不能晋级。本机 `runtime/data/live/quotes.sqlite`、`runtime/data/live/daily_bars.sqlite` 和完整归档需另行纳入授权的本地备份；Supabase 导出不包含它们。
- 不变更 Agent SDK，不接下单。仅本次覆盖美股慢资料；港股/A 股未获得同等证据底座。调度时间依本机时区，不代表美东开盘；盘中/盘外资格按美股交易时段另行判断。
