"""FastAPI 入口：只读适配 + 唯一写接口 verdict。生产静态托管 web/dist。

启动（仓库根目录，.venv-sc）：
    .venv-sc/bin/python -m uvicorn api.main:app --port 8000
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import evidence, recompute as recompute_mod, workbench

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="miOption Workbench API", docs_url="/api/docs", openapi_url="/api/openapi.json")

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/api/tickers")
def get_tickers():
    return {"tickers": workbench.list_tickers()}


@app.get("/api/console/{ticker}")
def get_console(ticker: str):
    return workbench.build_console(ticker)


@app.get("/api/console/{ticker}/field/{field_id}")
def get_field(ticker: str, field_id: str):
    return evidence.field_detail(ticker, field_id)


@app.get("/api/watchlist")
def get_watchlist():
    return workbench.build_watchlist()


@app.get("/api/tickers/{ticker}/cards")
def get_cards(ticker: str):
    return {"cards": workbench.build_cards(ticker)}


class VerdictBody(BaseModel):
    verdict: str | None  # adopt | watch | reject | null(清空)


@app.post("/api/cards/{card_id}/verdict")
def post_verdict(card_id: str, body: VerdictBody):
    result = workbench.save_verdict(card_id, body.verdict)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/api/evidence/coverage")
def get_coverage(tickers: str = ""):
    ts = [t for t in tickers.split(",") if t] or [t["ticker"] for t in workbench.list_tickers()]
    return evidence.coverage_matrix(ts)


@app.get("/api/evidence/runs/{ticker}")
def get_runs(ticker: str):
    return evidence.run_ledger(ticker)


@app.get("/api/evidence/risk")
def get_risk(ticker: str = "US.AAPL"):
    return evidence.risk_panel(ticker)


@app.get("/api/strategies")
def get_strategies():
    return {"strategies": evidence.strategies()}


class RecomputeBody(BaseModel):
    ticker: str
    quote: float | None = None
    sma5: float | None = None
    sma20: float | None = None
    flow: float | None = None
    rsi14: float | None = None
    iv30: float | None = None
    earningsGap: float | None = None


@app.post("/api/recompute")
def post_recompute(body: RecomputeBody):
    overrides = body.model_dump(exclude={"ticker"})
    return recompute_mod.recompute(body.ticker, overrides)


# ---- 生产静态托管（web/dist 存在时）。API 路由优先。 ----
if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        target = WEB_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")
