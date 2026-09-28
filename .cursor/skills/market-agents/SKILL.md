---
name: market-agents
description: Use this skill when the user asks about a US stock's data, trend, value, research, decision, structure menu, or a review of that workflow. Always run data, then decision, then review.
---

# 取数、研究决策、review

不管问句是要数据、要判断还是要结构，顺序都是 `data_agent`、`decision_agent`、`review_agent`。不能调换，也不能跳过。简报在 review 之后。

港股和 A 股直接拒绝，不要发请求。标的对不上唯一 `name` 就停下来问。

## 取数

`data_agent` 的唯一工具是 harness 执行的 `load`。不要改取数顺序，不要新造数据源。缺失保持缺失。切片名是 quote、kline、sma、flow、chain、fundamentals、earnings、filing、business、competition、risk、governance、news、social、events、macro。

## 研究决策

`decision_agent` 不取数。没有快照就拒绝。它在同一次里并列写出趋势、价值、研究，然后合成、筛结构、过风控。趋势是规则，只看报价、5 日均线和资金净额。价值看财报和申报摘录。研究看全部切片和价值备忘录，不改价值的判断，也不读趋势的结果。弃权不投票。合成不改写三份信号的方向。

## Review

`review_agent` 紧跟研究决策，没有决策记录就拒绝。它不取数，不改方向。只报告这些毛病：该跳过的源却用了、失败被写成可用、价值主张里的数字切片对不上、弃权票参与了合成、合成改写了某一份信号的方向。没有就写通过。发现毛病不换数据源重跑。简报还没写，不在检查范围里。
