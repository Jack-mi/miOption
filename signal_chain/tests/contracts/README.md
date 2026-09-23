# 契约测试（golden-file）

每个引擎一套：M0 真实产物存档为 fixture，适配器输出与期望快照比对。
上游升级或数据源疑似变动时重跑；测试红 = 适配器破损。

- `fixtures/tradingagents/` — TA state.json 样本（M0 后从 runs/ta/ 拷贝）
- `fixtures/dsa/` — DSA report_YYYYMMDD.md 样本（M0 后从 vendor DSA reports/ 拷贝）
- `test_ta_contract.py` / `test_dsa_contract.py` — 由 M0 真实产物生成期望值后启用
