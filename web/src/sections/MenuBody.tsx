/* 03 下半：结构菜单（分组折叠 + 带合约条目总表） */
import { useMemo, useState } from "react";
import { bi } from "../i18n";
import { fmtPct } from "../lib/format";
import { groupLabels, groupLabelsEn, menuStatusLabels, menuStatusLabelsEn } from "../lib/labels";
import { Legs, Payoff, ToneBadge } from "../components/ui";
import type { Workbench } from "../lib/api";

const GROUPS = ["bull", "bear", "neutral", "hedge"] as const;

function MenuItem({ item, open, onToggle, limits, spot }: {
  item: Workbench["menu"][number]; open: boolean; onToggle: () => void;
  limits: Record<string, any>; spot: number | null;
}) {
  const [showPayoff, setShowPayoff] = useState(false);
  const d = item.decision;
  const p = item.proposal;
  const statusLabel = bi(menuStatusLabels[item.status] || item.status, menuStatusLabelsEn[item.status] || item.status);
  const hasLegs = !!(p && p.legs && p.legs.length);

  return (
    <div className="menu-item" data-status={item.status}
      data-expandable={hasLegs ? "1" : undefined}
      onClick={hasLegs ? onToggle : undefined}
      role={hasLegs ? "button" : undefined}
      aria-expanded={hasLegs ? open : undefined}>
      <div className="menu-name">
        {hasLegs ? <span className="caret" data-open={open ? "1" : undefined} style={{ marginRight: 6 }}>▶</span> : null}
        {item.name}
        <small>{item.nameEn}</small>
      </div>

      <div>
        <div className="menu-body">{item.reason}</div>

        {hasLegs && open ? (
          <>
            <div style={{ marginTop: 9, display: "flex", gap: 22, flexWrap: "wrap", alignItems: "flex-start" }}>
              <div style={{ minWidth: 300, flex: "1 1 340px" }}>
                <div className="eyebrow" style={{ marginBottom: 5 }}>
                  {bi("契约腿 · legs（真实链上合约）", "Legs · real chain contracts")}
                </div>
                <Legs legs={p.legs} />
                <div style={{ marginTop: 9, display: "flex", gap: 18, flexWrap: "wrap", fontSize: 10.5, fontFamily: "var(--font-mono)" }}>
                  <span>
                    {bi("净权利金", "net premium")}{" "}
                    {p.net_premium != null ? (
                      <>
                        <b style={{ color: p.net_premium >= 0 ? "var(--pos)" : "var(--neg)" }}>
                          {p.net_premium >= 0 ? "+" : ""}{(p.net_premium * 100).toFixed(0)} USD
                        </b>{" "}
                        <span style={{ color: "var(--ink-4)" }}>
                          {p.net_premium >= 0 ? bi("净收入 credit", "credit") : bi("净支出 debit", "debit")}
                        </span>
                      </>
                    ) : <b>—</b>}
                  </span>
                  <span>{bi("最大亏损", "max loss")} <b>{p.max_loss == null ? bi("无上限", "unlimited") : p.max_loss}</b></span>
                  <span>{bi("最大盈利", "max profit")} <b>{p.max_profit == null ? bi("无上限", "unlimited") : p.max_profit}</b></span>
                  <span>short-vol <b>{p.is_short_vol ? bi("是", "yes") : bi("否", "no")}</b></span>
                </div>
              </div>

              <div style={{ flex: "0 1 330px", minWidth: 260 }}>
                <div className="eyebrow" style={{ marginBottom: 5 }}>
                  {bi("到期损益", "Payoff at expiry")}
                  <button className="btn" style={{ marginLeft: 8, padding: "1px 7px", fontSize: 10 }}
                    onClick={(e) => { e.stopPropagation(); setShowPayoff((v) => !v); }}>
                    {showPayoff ? bi("收起", "Hide") : bi("展开图", "Show")}
                  </button>
                </div>
                {showPayoff ? (
                  <Payoff proposal={p} spot={spot} />
                ) : (
                  <div style={{ fontSize: 10.5, color: "var(--ink-4)", lineHeight: 1.6 }}>
                    {bi("由 legs 与净权利金推导；行权价用虚线，现价用强调色竖线。",
                      "Derived from legs and net premium; strikes dashed, spot accent.")}
                  </div>
                )}
              </div>
            </div>

            {d ? (
              <div style={{ marginTop: 10 }}>
                {d.approved ? (
                  <div className="risk-note" data-k="ok">
                    ✓ {bi("结构检查通过", "Structure checks passed")}
                  </div>
                ) : (
                  <>
                    <div className="risk-note" data-k="veto">✕ {bi("否决", "Vetoed")}：{(d.vetoes || []).join("；")}</div>
                    {(d.warnings || []).map((w, i) => (
                      <div className="risk-note" data-k="warn" key={i}>△ {w}</div>
                    ))}
                  </>
                )}
              </div>
            ) : null}

            <div style={{ marginTop: 8, fontSize: 9.5, color: "var(--ink-4)", fontFamily: "var(--font-mono)" }}>
              {bi("门禁输入", "gate inputs")}：min_open_interest {limits.min_open_interest} · max_spread_pct {fmtPct(limits.max_spread_pct, 0)}
              {" · "}max_position_risk_pct {fmtPct(limits.max_position_risk_pct, 0)}
              {" · "}dte {limits.dte_min}~{limits.dte_max} · widths {(limits.widths || []).join(" / ")}
            </div>
          </>
        ) : hasLegs ? (
          <div style={{ marginTop: 6, fontSize: 10.5, color: "var(--ink-4)", fontFamily: "var(--font-mono)" }}>
            {p.legs.length} {bi("条腿", "legs")} · {d && !d.approved ? bi("已否决", "vetoed") : bi("待展开", "expand")}
          </div>
        ) : null}
      </div>

      <div className="menu-verdict-badge" style={{ flexDirection: "column", alignItems: "flex-end", gap: 5 }}>
        <ToneBadge
          tone={item.status === "fit" ? "pos" : item.status === "unfit" ? "mute" : "na"}
          title={"render_menu status = " + item.status}>
          {statusLabel}
        </ToneBadge>
        {hasLegs && d ? (
          <ToneBadge tone={d.approved ? "accent" : "neg"} stop={!d.approved} title="RiskDecision">
            {d.approved ? bi("通过", "Pass") : bi("否决", "Veto")}
          </ToneBadge>
        ) : null}
        {item.tier ? (
          <ToneBadge tone="mute" title={"收租评级 tier = " + item.tier}>{item.tier}</ToneBadge>
        ) : null}
      </div>
    </div>
  );
}

export function MenuBody({ t, filter }: { t: Workbench; filter: string }) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ bull: true, bear: false, neutral: false, hedge: false });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const byGroup = useMemo(() => {
    const m: Record<string, Workbench["menu"]> = { bull: [], bear: [], neutral: [], hedge: [] };
    GROUPS.forEach((g) => {
      m[g] = t.menu.filter((x) => x.group === g)
        .filter((x) => filter === "all" || x.status === filter);
    });
    return m;
  }, [t.menu, filter]);

  const withLegs = t.menu.filter((x) => x.proposal && x.proposal.legs);

  return (
    <>
      <div className="panel">
        {GROUPS.map((g) => {
          const items = byGroup[g];
          const open = openGroups[g];
          const total = t.menu.filter((x) => x.group === g).length;
          return (
            <div className="menu-group" key={g} style={{ marginBottom: 0 }}>
              <button className="menu-group-head" onClick={() => setOpenGroups((s) => ({ ...s, [g]: !s[g] }))}
                aria-expanded={open}>
                <span className="caret" data-open={open ? "1" : undefined}>▶</span>
                <span className="menu-group-name">{bi(groupLabels[g], groupLabelsEn[g])}</span>
                <span className="menu-count">{items.length} / {total}</span>
                <span className="menu-legend">
                  {(["fit", "unfit", "impossible"] as const).map((s) => {
                    const n = t.menu.filter((x) => x.group === g && x.status === s).length;
                    return n ? (
                      <ToneBadge key={s} tone={s === "fit" ? "pos" : s === "unfit" ? "mute" : "na"}>
                        {bi(menuStatusLabels[s], menuStatusLabelsEn[s])} {n}
                      </ToneBadge>
                    ) : null;
                  })}
                </span>
              </button>
              {open ? (
                items.length ? items.map((item, i) => (
                  <MenuItem key={item.nameEn + "-" + i} item={item} limits={t.risk.limits}
                    spot={t.chain ? t.chain.spot : t.spot}
                    open={!!expanded[item.nameEn + "-" + i]}
                    onToggle={() => setExpanded((s) => ({ ...s, [item.nameEn + "-" + i]: !s[item.nameEn + "-" + i] }))} />
                )) : (
                  <div style={{ padding: "18px var(--pad)", fontSize: 11, color: "var(--ink-4)" }}>
                    {bi("当前筛选下这一组没有条目。", "No entries in this group under the current filter.")}
                  </div>
                )
              ) : null}
            </div>
          );
        })}
      </div>

      {withLegs.length ? (
        <div style={{ marginTop: 16 }}>
          <div className="eyebrow" style={{ marginBottom: 9 }}>
            {bi("带真实合约的条目", "Entries with real contracts")} · {withLegs.length} / {t.menu.length}
          </div>
          <table className="tbl">
            <thead>
              <tr>
                <th>{bi("结构", "Structure")}</th><th>{bi("方向组", "Group")}</th><th className="c">{bi("腿数", "Legs")}</th>
                <th className="r">{bi("净权利金", "Net premium")}</th><th className="r">{bi("最大亏损", "Max loss")}</th>
                <th className="c">short-vol</th><th>{bi("风控", "Risk")}</th>
              </tr>
            </thead>
            <tbody>
              {withLegs.map((x, i) => (
                <tr key={x.nameEn + "-" + i} data-stop={x.decision && !x.decision.approved ? "1" : undefined}>
                  <td>{x.name} <span className="mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>{x.nameEn}</span></td>
                  <td style={{ fontSize: 11, color: "var(--ink-3)" }}>{bi(groupLabels[x.group], groupLabelsEn[x.group])}</td>
                  <td className="c mono">{x.proposal!.legs.length}</td>
                  <td className="r mono" style={{ color: (x.proposal!.net_premium ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                    {x.proposal!.net_premium != null
                      ? (x.proposal!.net_premium >= 0 ? "+" : "") + (x.proposal!.net_premium * 100).toFixed(0)
                      : "—"}
                  </td>
                  <td className="r mono">{x.proposal!.max_loss == null ? bi("无上限", "Unlimited") : x.proposal!.max_loss}</td>
                  <td className="c">{x.proposal!.is_short_vol ? bi("是", "Yes") : bi("否", "No")}</td>
                  <td>
                    {x.decision
                      ? (x.decision.approved
                        ? <ToneBadge tone="pos">{bi("通过", "Pass")}</ToneBadge>
                        : <ToneBadge tone="neg" stop>{bi("否决", "Veto")}</ToneBadge>)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );
}
