"""FastMCP stdio server. Policy stays in ToolRuntime; this module is the protocol shell."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .tool_handlers import ToolRuntime

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
_TRADE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)
_RESEARCH_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


def build_mcp(runtime: ToolRuntime | None = None) -> FastMCP:
    rt = runtime or ToolRuntime()
    mcp = FastMCP("mioption")

    @mcp.tool(annotations=_READ, tags={"knowledge"})
    def wiki_query(query: str, top: int = 5) -> dict[str, Any]:
        """Read-only vault retrieval. Use for strategy meaning and published P/L; never invent numbers."""
        return rt.dispatch("wiki_query", {"query": query, "top": top})

    @mcp.tool(annotations=_READ, tags={"trade"})
    def futu_probe() -> dict[str, Any]:
        """Probe OpenD connectivity and high-level account permissions (no orders)."""
        return rt.dispatch("futu_probe", {})

    @mcp.tool(annotations=_READ, tags={"trade"})
    def futu_quote_chain(underlying: str, expiry: str | None = None) -> dict[str, Any]:
        """Fetch an option chain for an underlying (mock unless MIOPTION_FUTU_MOCK=0)."""
        args: dict[str, Any] = {"underlying": underlying}
        if expiry:
            args["expiry"] = expiry
        return rt.dispatch("futu_quote_chain", args)

    @mcp.tool(annotations=_TRADE, tags={"trade"})
    def futu_place_option_order(
        underlying: str,
        code: str,
        side: str = "BUY",
        qty: float = 1,
        price: float | None = None,
        env: str = "SIMULATE",
        structure_id: str | None = None,
        naked_short: bool = False,
    ) -> dict[str, Any]:
        """Place an option order. Default env=SIMULATE. REAL requires policy unlock."""
        return rt.dispatch(
            "futu_place_option_order",
            {
                "underlying": underlying,
                "code": code,
                "side": side,
                "qty": qty,
                "price": price,
                "env": env,
                "structure_id": structure_id,
                "naked_short": naked_short,
            },
        )

    @mcp.tool(annotations=_TRADE, tags={"trade"})
    def bot_run_automation(
        kind: str = "agent",
        webhook_id: str | None = None,
        context_json: str | None = None,
    ) -> dict[str, Any]:
        """Run bot automations for a trigger kind (webhook/agent/button/schedule)."""
        args: dict[str, Any] = {"kind": kind}
        if webhook_id:
            args["webhook_id"] = webhook_id
        if context_json:
            args["context_json"] = context_json
        return rt.dispatch("bot_run_automation", args)

    @mcp.tool(annotations=_RESEARCH_WRITE, tags={"trade"})
    def seller_scan(underlyings: str | None = None) -> dict[str, Any]:
        """Scan OpenD watchlist for bull-put / bear-call cards. Does not call OSM."""
        args: dict[str, Any] = {}
        if underlyings:
            args["underlyings"] = underlyings
        return rt.dispatch("seller_scan", args)

    @mcp.tool(annotations=_READ, tags={"trade"})
    def seller_list_cards(status: str | None = None) -> dict[str, Any]:
        """List local seller-desk cards."""
        args: dict[str, Any] = {}
        if status:
            args["status"] = status
        return rt.dispatch("seller_list_cards", args)

    @mcp.tool(annotations=_RESEARCH_WRITE, tags={"trade"})
    def seller_verdict(card_id: str, verdict: str, note: str = "") -> dict[str, Any]:
        """Record adopt/watch/reject. Does not place an order."""
        return rt.dispatch(
            "seller_verdict",
            {"card_id": card_id, "verdict": verdict, "note": note},
        )

    @mcp.tool(annotations=_RESEARCH_WRITE, tags={"trade"})
    def seller_monitor_tick() -> dict[str, Any]:
        """Mark tracked cards; emit protect/TP/settle events. Remind-only."""
        return rt.dispatch("seller_monitor_tick", {})

    if os.environ.get("MIOPTION_RESEARCH_ONLY") == "1":
        mcp.disable(names={"futu_place_option_order", "bot_run_automation"}, components={"tool"})
    return mcp


mcp = build_mcp()


def main() -> int:
    mcp.run(show_banner=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
