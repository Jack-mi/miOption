/* 错误边界：单个字段/区块渲染失败不能把整页打成黑屏。 */
import React from "react";
import { bi } from "../i18n";

export class Boundary extends React.Component<
  { children: React.ReactNode },
  { err: Error | null }
> {
  constructor(p: { children: React.ReactNode }) {
    super(p);
    this.state = { err: null };
  }
  static getDerivedStateFromError(err: Error) {
    return { err };
  }
  componentDidCatch(err: Error, info: React.ErrorInfo) {
    if (window.console) console.error("[miOption] render failed:", err, info);
  }
  render() {
    if (this.state.err) {
      return (
        <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)", background: "var(--neg-soft)" }}>
          <b>{bi("这块内容渲染失败", "This block failed to render")}</b>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}>
            {String(this.state.err && this.state.err.message || this.state.err)}
          </span>
        </div>
      );
    }
    return this.props.children;
  }
}
