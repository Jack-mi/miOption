/* 基础格式化。数字一律等宽 + tabular-nums（样式里保证）。 */
export const nf = new Intl.NumberFormat("en-US");

export function fmtPct(v: number | null | undefined, d = 1): string | null {
  if (v == null || Number.isNaN(v)) return null;
  return (v * 100).toFixed(d) + "%";
}

export function fmtNum(v: number | null | undefined, d = 2): string | null {
  if (v == null || Number.isNaN(v)) return null;
  return (v as number).toFixed(d);
}

export function fmtMoney(v: number | null | undefined, d = 0): string | null {
  if (v == null || Number.isNaN(v)) return null;
  return "$" + nf.format(+(+(v as number)).toFixed(d));
}

export function fmtSigned(v: number | null | undefined, d = 2): string | null {
  if (v == null || Number.isNaN(v)) return null;
  return ((v as number) > 0 ? "+" : "") + (v as number).toFixed(d);
}

export function fmtDelta(a: number | null | undefined, b: number | null | undefined): number | null {
  if (a == null || b == null || !b) return null;
  return (a - b) / b;
}
