# miOption Workbench Web（api/ + web/）

只读投研工作台的 Web 交付。**不改动 `signal_chain/` 与 `runtime/` 任何一行 agentic 代码**；
api 直接读文件系统产物（`runs/`、`chains/`、`reports/`、`runtime/data/live/seller/`、
`knowledge/wiki/strategies/`、`signal_chain/config.yaml`），并通过 import 复用链路里的
确定性函数（`screen_menu` / `combine` / 走势两分制）。跑批仍只走 CLI，web 不提供触发新运行的入口。

## 启动

```bash
# 一次性：装 api 依赖（进 .venv-sc）
.venv-sc/bin/pip3 install -r api/requirements.txt

# 一次性：构建前端（生成 web/dist，生产由 FastAPI 静态托管，单进程交付）
cd web && npm install && npm run build && cd ..

# 启动（api + 前端同一个进程）
.venv-sc/bin/python -m uvicorn api.main:app --port 8000
# 打开 http://127.0.0.1:8000/
```

开发模式（改前端即时生效）：

```bash
.venv-sc/bin/python -m uvicorn api.main:app --port 8000   # 终端 1
cd web && npm run dev                                     # 终端 2，vite proxy /api → 8000
```

## 测试

```bash
.venv-sc/bin/python -m pytest api/tests/ -q
```

## API（全部只读，除 verdict）

| 路由 | 说明 |
|---|---|
| `GET /api/tickers` | 标的列表 + 状态徽章（watchlist ∪ 最新 runs ∪ seller 卡） |
| `GET /api/console/{ticker}` | 决策台聚合：报价/技术面/18 字段/三信号/合成/信号闸/链快照/菜单/简报/候选卡 |
| `GET /api/console/{ticker}/field/{field_id}` | 单字段惰性详情 |
| `GET /api/watchlist` | 观察清单主表行 |
| `GET /api/tickers/{ticker}/cards` | seller 候选卡（历史卡降级「仅观察」，只改展示） |
| `POST /api/cards/{card_id}/verdict` | 唯一写接口。`{verdict: "adopt"\|"watch"\|"reject"\|null}`，走 `apply_verdict` 与 CLI 同一份真相 |
| `GET /api/evidence/coverage?tickers=…` | 字段覆盖矩阵 |
| `GET /api/evidence/runs/{ticker}` | 运行台账 |
| `GET /api/evidence/risk?ticker=…` | 阈值与账户 |
| `GET /api/strategies` | 27 张策略百科笔记 |
| `POST /api/recompute` | 数据源编辑器重算（走势两分制 + combine v5 + 财报窗口/min_conviction 门禁），纯确定性 |

## 关键纪律

- **菜单腿重放**：台账 `risk.menu[]` 是状态/档位/vetoes/max_loss 的权威；`api/menu_replay.py`
  用链快照 + ledger signal rows 重跑 `combine` + `screen_menu` 只补合约腿用于展示。
  重放与台账不一致或腿重构失败 → 该行不可展开（一处兜底 try/except，不阻断页面）。
- **缺失语义**：`FieldMeta.status` 四态原样透传；无台账标的是第五态 `unknown`（灰），不是 missing（红）。绝不把缺字段补 0。
- **verdict**：前端四按钮 采纳/观察/拒绝/清空 → `apply_verdict`；历史卡一律降级「仅观察」并追加理由（只改展示，不写回）。
- **时段**：「盘中/盘外」不是用户开关，只按卡片自身盘口时效判档，页面只读展示。

## 数据回填（可选，挂定时任务）

```bash
# 日线落库（DailyStore，60 日 K 线图的来源）
.venv-sc/bin/python -m api.backfill_daily_bars HK.09992 HK.03690 US.AAPL

# IV/HV 分位快照（iv30 / ivRank 的来源，观察清单错价窗口用）
runtime/.venv/bin/python -m api.backfill_vol_basis US.AAPL HK.09992 HK.03690
```

注：`underlying_bridge.main()` 曾把 `--scan-days` 误读为 `history_start`（argv 错位），
已在本体修复——`main()` 先剥离 flag 再取位置参数，`probe()` 显式接收 `history_start`。
