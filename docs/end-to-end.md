# miOption 端到端运行与验收

核验日期：2026-09-20。交付对象为本地期权研究工作台，不是自动实盘交易系统。

## 启动

在仓库根目录执行：

```bash
runtime/.venv/bin/python runtime/scripts/serve_h5.py --mode mock --chat
```

真实行情模式先启动并登录本机 Futu OpenD（默认 `127.0.0.1:11111`），再使用：

```bash
runtime/.venv/bin/python runtime/scripts/serve_h5.py --mode live --chat
```

入口：

- `http://127.0.0.1:8765/`：知识地图。
- `http://127.0.0.1:8765/chain.html`：标的行情和期权链；拉取才请求 OpenD，刷新读取 SQLite。
- `http://127.0.0.1:8765/desk.html`：扫描、裁决、监控与研究事件。
- `http://127.0.0.1:8765/chat.html`：OpenCode + miOption MCP 知识问答和研究工具。

H5 端口由 `--port` 指定；chat 端口由 `--chat-port` 指定，默认 `4097`。本机 `8787` 已属于其他服务，不抢占。模型通过 `--model provider/model` 设置，默认 `opencode-go/deepseek-v4-flash`；必须已具备该 provider 的本地认证。没有 OpenCode 时省略 `--chat`，行情和卖方研究仍可运行。终端 Ctrl-C 正常退出并停止启动器自己的 chat 子进程。不自动常驻、不创建定时任务。

## 数据与执行边界

- 默认 mock 存在 `runtime/data/mock/`；live 存在 `runtime/data/live/`。支持 `--data-dir`，启动时打印实际路径。
- 旧 `runtime/data/seller/` 和 `runtime/data/quotes.sqlite` 原样保留，不与新模式静默混用。验收前另有本地备份 `/tmp/mioption-before-e2e.OueDfJ/data`。
- H5 与 chat MCP 通过环境变量共享目录、模式。CLI 用 `MIOPTION_FUTU_MOCK=0` 指向 live；默认指向 mock。
- `MIOPTION_RESEARCH_ONLY=1` 同时禁用 MCP 下单/订单自动化工具和底层 dispatch；H5 没有订单 endpoint。
- 决策文件原子替换，研究操作跨进程加锁。重新扫描不删除已裁决/跟踪卡片，也不重置其原始收益成本基础。
- 时间戳缺失或拉取距今超过 72 小时的快照拒绝扫描与监控。这个阈值不是交易所实时性保证；页面保留拉取时间、来源与行情原始字段。mock 不能标记 live 卡。
- 到期卡片发 `expiry_review`，必须另行确认券商结算/指派；保护和滚动目前仍是建议，不自动执行。

## 本轮真实验收证据

1. OpenD 只读连接成功，quote context 可用。
2. `POST /api/chain/pull` 拉取 `US.BIDU`，时间 `2026-09-20T08:07:58.471027+00:00`；612 个合约、6 个到期日，564 个包含报价，612 个包含 Greeks。数据库和浏览器显示一致。
3. `POST /api/seller/scan` 产生 1 张符合默认筛选的候选，来源 `futu`，不是 mock。候选标识 `US.BIDU-2026-10-02-bear_call_spread-95-100`；数量少或为零是有效结果，不降低筛选条件凑数。
4. 浏览器临时采纳该卡；执行 `MIOPTION_FUTU_MOCK=0 runtime/.venv/bin/python runtime/scripts/seller_follow.py --whitelist US.BIDU` 返回 `mode=dry_run`、`placed=false`、`submit=false`，未创建券商订单。
5. 浏览器点击监控，得到研究性买回成本标记与一条 `protect` 事件，`place_order=false`。该记录不表示已实现交易收益，也不是投资建议。验收结束后已清除临时采纳；保留的验收事件可追溯。
6. 浏览器真实对话调用 `mioption_wiki_query`，拿到策略全文和 `page_path`，返回中文回答。此项证明检索与回答链路可用，不构成金融内容质量的全面审计。
7. 停止并重新启动工作台后，行情、卡片、事件仍从同一目录读取；旧对话可加载。模型和 API 认证沿用本机配置，未写入仓库。
8. 真实浏览器第二轮读取 `seller_list_cards`，与研究台同一张卡的来源、时间、裁决一致。第三轮 `seller_scan` 先显示许可卡，点击“允许一次”后调用完成，无残留权限请求、无错误、没有重复用户气泡。
9. 合约单元格可打开详情抽屉，研究卡的来源笔记接口可读到腿结构与指派风险。桌面没有横向溢出；390px 移动视口的对话输入区完整可见。对话截图保存在本机 `/tmp/mioption-e2e-chat-20260920.png`。

## 自动验收

```bash
scratch=$(mktemp -d)
PYTHONPATH=runtime MIOPTION_FUTU_MOCK=1 MIOPTION_SELLER_DIR="$scratch/seller" MIOPTION_QUOTES_DB="$scratch/quotes.sqlite" runtime/.venv/bin/python -m pytest runtime/tests -q
python3 scripts/probe.py --check
python3 scripts/build_knowledge.py --check
python3 vendor/claude-obsidian/scripts/claude-obsidian.py doctor --vault knowledge
python3 vendor/claude-obsidian/scripts/claude-obsidian.py lint --vault knowledge --as-of 2026-09-20
node --check docs/vault-map/chat.js
node --check docs/vault-map/chain.js
node --check docs/vault-map/desk.js
git diff --check
```

2026-09-20：59 项 Python 测试通过；存在 futu SDK `setDaemon` 弃用警告，不影响本轮测试。`build_knowledge.py --check` 返回 393 chunks / 10 items / 22 strategies / 5 relations；这是冻结归档，不是 vault 的 27 张策略。

## 尚未启用的能力

- 自动实盘下单、自动移仓/保护、无人值守轮询和券商最终结算对账均未启用。
- 单独 CLI 的 sequential submit 路径保留，但未向券商提交验收订单，不声明此路径实盘可用。
- 知识库来源新增审核和全站爬取不属于本轮；原抓取约束不变。
- 工作区修改尚未 commit/push，未覆盖先前未提交改动。
