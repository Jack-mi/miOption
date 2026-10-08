/* 枚举标签。枚举值本身（available / conflicted / US.AAPL）是契约名，不翻译。 */

export const statusLabels: Record<string, string> = {
  available: "可用", missing: "缺失", unsupported: "不支持", stale: "过期", unknown: "无记录",
};
export const statusLabelsEn: Record<string, string> = {
  available: "available", missing: "missing", unsupported: "unsupported", stale: "stale", unknown: "no record",
};
export const directionLabels: Record<string, string> = {
  strong_buy: "强烈看多", buy: "看多", neutral: "中性", sell: "看空", strong_sell: "强烈看空",
};
export const directionLabelsEn: Record<string, string> = {
  strong_buy: "Strong Buy", buy: "Buy", neutral: "Neutral", sell: "Sell", strong_sell: "Strong Sell",
};
export const agreementLabels: Record<string, string> = {
  aligned: "互相印证", partial: "部分一致", conflicted: "方向分歧",
  single_source: "单源", insufficient_data: "数据不足",
};
export const agreementLabelsEn: Record<string, string> = {
  aligned: "Aligned", partial: "Partial", conflicted: "Conflicted",
  single_source: "Single source", insufficient_data: "Insufficient data",
};
export const dataStatusLabels: Record<string, string> = {
  actionable: "可行动", opinion: "观点", insufficient_data: "数据不足",
};
export const dataStatusLabelsEn: Record<string, string> = {
  actionable: "Actionable", opinion: "Opinion", insufficient_data: "Insufficient",
};
export const tierLabelsEn: Record<string, string> = {
  "可考虑": "Considerable",
  "条件可考虑，开盘须重报价": "Conditional — requote at open",
  "仅观察": "Watch only",
  "禁做": "Blocked",
};
export const groupLabels: Record<string, string> = {
  bull: "看涨方向", bear: "看跌方向", neutral: "中性 · 波动率", hedge: "对冲 · 保护",
};
export const groupLabelsEn: Record<string, string> = {
  bull: "Bullish", bear: "Bearish", neutral: "Neutral / Vol", hedge: "Hedge",
};
export const menuStatusLabels: Record<string, string> = {
  fit: "适合", unfit: "不适合", impossible: "做不了",
};
export const menuStatusLabelsEn: Record<string, string> = {
  fit: "Fit", unfit: "Unfit", impossible: "Impossible",
};
