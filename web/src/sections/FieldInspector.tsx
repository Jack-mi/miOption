/* 单个字段的完整溯源。详情惰性获取：点开时才调 field 接口。 */
import { useEffect, useState } from "react";
import { bi } from "../i18n";
import { api, SourceField } from "../lib/api";
import { FieldBadge } from "../components/ui";
import { Boundary } from "../components/Boundary";

interface Detail { rows: [string, unknown][]; note: string; }

export function FieldInspector({ s, ticker }: { s: SourceField; ticker: string }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setDetail(null);
    setErr(null);
    api.fieldDetail(ticker, s.id)
      .then((d) => { if (alive) setDetail(d); })
      .catch((e) => { if (alive) setErr(String(e && e.message || e)); });
    return () => { alive = false; };
  }, [ticker, s.id]);

  const meta: [string, string][] = [
    ["status", s.state],
    ["source", s.source || "—"],
    ["as_of", s.as_of || "—"],
    ["fetched_at", s.fetched_at || "—"],
    ["timezone", s.timezone || "—"],
    ["period", s.period || "—"],
    ["market_time", s.market_time || "—"],
    ["error", s.error || "—"],
  ];
  return (
    <div style={{ padding: "14px 16px", background: "var(--surface-2)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 10 }}>
        <FieldBadge state={s.state} />
        <span style={{ fontWeight: 600 }}>{s.field}</span>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginLeft: "auto" }}>{s.id}</span>
      </div>

      <div style={{ fontSize: 11.5, color: "var(--ink-2)", marginBottom: 11 }}>{s.note}</div>

      {s.preview ? (
        <div className="caveat" style={{
          marginBottom: 11, borderStyle: "solid",
          borderColor: s.state === "available" ? "var(--rule-strong)" : s.state === "missing" ? "var(--neg)" : "var(--na)",
        }}>
          <b>{bi("取值", "Value")}</b>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}>{s.preview}</span>
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px,1fr))", gap: 0,
        border: "var(--hair) solid var(--rule)", background: "var(--surface)" }}>
        {meta.map(([k, v]) => (
          <div className="field" key={k} style={{ borderBottom: "var(--hair) solid var(--rule)" }}>
            <span className="field-name mono" style={{ fontSize: 10 }}>{k}</span>
            <span className="mono" style={{
              marginLeft: "auto", fontSize: 10.5,
              color: k === "error" && v !== "—" ? "var(--neg)" : k === "status" ? "var(--ink)" : "var(--ink-2)",
            }}>{v}</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          {bi("这个字段自己的内容", "This field's own content")}
        </div>
        <Boundary>
          {err ? (
            <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}>
              <b>{bi("字段详情取不到", "Field detail unavailable")}</b>
              <span className="mono" style={{ fontSize: 10.5 }}>{err}</span>
            </div>
          ) : !detail ? (
            <div style={{ fontSize: 11, color: "var(--ink-4)" }}>…</div>
          ) : detail.rows && detail.rows.length ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px,1fr))", gap: 0,
                border: "var(--hair) solid var(--rule)", background: "var(--surface)" }}>
                {detail.rows.map(([k, v], i) => (
                  <div className="field" key={i} style={{ alignItems: "baseline" }}>
                    <span className="field-name mono" style={{ fontSize: 10 }}>{k}</span>
                    <span className="mono" style={{
                      marginLeft: "auto", fontSize: 10.5,
                      color: String(v) === "missing" ? "var(--neg)" : "var(--ink)",
                    }}>{String(v)}</span>
                  </div>
                ))}
              </div>
              {detail.note ? (
                <div style={{ fontSize: 11, color: "var(--ink-2)", lineHeight: 1.6, marginTop: 9 }}>
                  {detail.note}
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
              {bi("这个字段没有更多内容。", "No further content for this field.")}
            </div>
          )}
        </Boundary>
      </div>

      <div style={{ marginTop: 12 }}>
        <div className="eyebrow" style={{ marginBottom: 6 }}>
          {bi("字段约束", "Field constraints")}
        </div>
        <div className="gap-list">
          <div className="gap-item" style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}>{s.note}</div>
        </div>
      </div>
    </div>
  );
}
