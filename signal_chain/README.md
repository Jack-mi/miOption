# signal_chain — 美港股期权分析决策链

基于 Codex SDK 编排：TradingAgents + DSA 并行出信号 → Codex 合成 → Futu/yfinance 期权链+IV
→ Codex 策略选结构 → 确定性风控闸 → 中文决策简报。v1 只做决策支持，不下单。

## 架构

    orchestrator (纯 Python)
      ├─ engines/runner.py     TA/DSA 子进程（各自 vendor venv，并行，LLM→8790/8799）
      ├─ adapters/             引擎产物 → RawBundle（确定性映射）
      ├─ agents/codex.py       Codex SDK thread（Sandbox.read_only，output_schema + pydantic 复核）
      ├─ pipeline/steps.py     [CODEX] 抽取/合成说明/策略；确定性链摘要
      ├─ options/              Futu OpenD 取链桥（频控 pacing）+ yfinance 美股降级 + IV 派生
      ├─ risk/limits.py        风控闸：conflicted / 财报窗口 short-vol / 流动性 / 敞口
      ├─ synth/combine.py      Ensemble 合成规则（aligned/partial/conflicted/single_source）
      └─ storage.py            signals/ chains/ reports/ runs/ 落盘 + 台账

## 一次性 setup

    # 1. signal_chain 自身环境（Codex SDK + pydantic + yfinance）
    uv venv --python 3.12 .venv-sc
    uv pip install --python .venv-sc/bin/python openai-codex pydantic pyyaml yfinance pytest httpx

    # 2. 引擎 vendor（钉版见 vendor.lock.json）
    #    TA 必须 editable 安装，否则受管 patch 不进 site-packages（M0 实踩坑）
    cd vendor/TradingAgents && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e .
    git apply ../patches/tradingagents-responses-custom-baseurl.patch   # 新克隆时需要
    cd ../daily_stock_analysis && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt

    # 3. 8799 翻译 shim（litellm 组件必走，launchd 常驻）
    launchctl load ~/Library/LaunchAgents/com.mioption.signal-chain-shim.plist

    # 4. 前置服务：Futu OpenD (11111) 与 Friday 路由 (8790) 在线
    python scripts/upstream_check.py --probe

## 日常运行

    # 全链路（引擎 + Codex agents + 链 + 策略 + 风控 + 简报）
    .venv-sc/bin/python -m signal_chain.orchestrator --tickers US.AAPL,HK.00700

    # 分阶段
    --engines-only     # 只跑引擎+适配（M0 冒烟）
    --use-existing     # 复用 runs/ 下既有引擎产物，不重跑引擎
    --no-codex         # 跳过所有 Codex agent（纯确定性干跑）

    # 测试
    .venv-sc/bin/python -m pytest signal_chain/tests -q

    # 上游版本检查 / 升级演练（绝不自动升级）
    python scripts/upstream_check.py                # 只读对比
    python scripts/upstream_check.py --upgrade tradingagents   # 演练

## 模型与路由（config.yaml 显式钉版）

| 环节 | 路由 | 模型 |
|---|---|---|
| Codex 抽取/合成 | SDK → 8790 (Responses) | deepseek-v4.1-flash |
| Codex 策略 | SDK → 8790 | kimi-k3（gpt-6-sol 恢复后切回） |
| Codex 简报 | SDK → 8790 | kimi-k3 |
| TA deep / quick | → 8790（受管 patch 强制 Responses） | kimi-k3 / deepseek-v4.1-flash |
| DSA | → 8799 shim（litellm 不可直连 8790） | glm-5.3 |

## 已知坑（M0 实记，详见 UPSTREAM.md）

1. TA 必须 editable 安装；普通 install 会让 patch 静默失效（走 chat/completions 被 8790 打回 502）。
2. 8790 只说 Responses 且载荷瘦；litellm 直连必炸，DSA 一律走 8799 shim（DSA 流式请求会自动降级非流式）。
3. Futu OpenD `get_option_chain` 限 10 次/30 秒 —— bridge 已内置 pacing + 退避重试。
4. Futu `option_implied_volatility` 是百分数，bridge 已归一到小数。
5. DSA 首次运行初始化 sqlite，禁止两个 DSA 进程并发。
6. Yahoo 限流会让 TA 数据层整体不可用（NoMarketDataError），属环境因素，稍后重试即可。
