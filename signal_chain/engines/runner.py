"""引擎子进程编排：TA / DSA 并行跑，各自独立 venv，LLM 流量指向本机 8790。"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..config import (
    DSA_DIR,
    DSA_VENV_PY,
    REPO_ROOT,
    TA_DIR,
    TA_VENV_PY,
    NormTicker,
    Settings,
)

_ENGINE_TIMEOUT = 2400  # 40 分钟（多智能体辩论较慢）


@dataclass
class EngineRunResult:
    engine: str
    ok: bool
    out_dir: Path | None = None
    report_path: Path | None = None
    error: str | None = None
    elapsed_sec: float = 0.0


def _ta_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    models = settings.models
    env.update({
        "TRADINGAGENTS_LLM_PROVIDER": "openai_compatible",
        "TRADINGAGENTS_LLM_BACKEND_URL": f"{settings.router_base_url}/v1",
        "TRADINGAGENTS_FORCE_RESPONSES_API": "1",  # 受管 patch 开关
        "TRADINGAGENTS_DEEP_THINK_LLM": models["ta_deep_think"],
        "TRADINGAGENTS_QUICK_THINK_LLM": models["ta_quick_think"],
        "TRADINGAGENTS_RESULTS_DIR": str(settings.ta_results_dir()),
    })
    return env


def _dsa_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "LLM_CHANNELS": "FRIDAY",
        # 8790 只说 Responses 且载荷过瘦（litellm 解析炸），DSA 走本地翻译 shim
        "LLM_FRIDAY_BASE_URL": "http://localhost:8799/v1",
        "LLM_FRIDAY_API_KEY": "EMPTY",          # 8790 免鉴权，占位即可
        "LLM_FRIDAY_MODELS": settings.models["dsa"],
    })
    return env


async def run_tradingagents(t: NormTicker, trade_date: date, settings: Settings) -> EngineRunResult:
    out_dir = settings.ta_results_dir() / f"{trade_date.isoformat()}_{t.canonical.replace('.', '-')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    script = REPO_ROOT / "signal_chain" / "engines" / "run_ta.py"
    cmd = [str(TA_VENV_PY), str(script), t.ta_format, trade_date.isoformat(), str(out_dir)]
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, env=_ta_env(settings), cwd=str(TA_DIR),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_ENGINE_TIMEOUT)
        elapsed = loop.time() - start
        if proc.returncode != 0:
            return EngineRunResult("tradingagents", False, out_dir=out_dir,
                                   error=stderr.decode()[-800:], elapsed_sec=elapsed)
        state = out_dir / "state.json"
        if not state.exists():
            return EngineRunResult("tradingagents", False, out_dir=out_dir,
                                   error="state.json 未生成", elapsed_sec=elapsed)
        return EngineRunResult("tradingagents", True, out_dir=out_dir,
                               report_path=state, elapsed_sec=elapsed)
    except asyncio.TimeoutError:
        return EngineRunResult("tradingagents", False, out_dir=out_dir,
                               error=f"超时（>{_ENGINE_TIMEOUT}s）")


async def run_dsa(t: NormTicker, trade_date: date, settings: Settings) -> EngineRunResult:
    out_dir = settings.ta_results_dir().parent / "dsa" / f"{trade_date.isoformat()}_{t.canonical.replace('.', '-')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(DSA_VENV_PY), "main.py", "--stocks", t.dsa_format]
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, env=_dsa_env(settings), cwd=str(DSA_DIR),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_ENGINE_TIMEOUT)
        elapsed = loop.time() - start
        (out_dir / "stdout.log").write_text(stdout.decode(errors="replace")[-20000:], encoding="utf-8")
        (out_dir / "stderr.log").write_text(stderr.decode(errors="replace")[-20000:], encoding="utf-8")
        if proc.returncode != 0:
            return EngineRunResult("dsa", False, out_dir=out_dir,
                                   error=stderr.decode()[-800:], elapsed_sec=elapsed)
        report = DSA_DIR / "reports" / f"report_{trade_date.strftime('%Y%m%d')}.md"
        if not report.exists():
            candidates = sorted((DSA_DIR / "reports").glob("report_*.md"),
                                key=lambda p: p.stat().st_mtime, reverse=True)
            report = candidates[0] if candidates else report
        if not report.exists():
            return EngineRunResult("dsa", False, out_dir=out_dir,
                                   error="DSA 报告文件未找到", elapsed_sec=elapsed)
        return EngineRunResult("dsa", True, out_dir=out_dir,
                               report_path=report, elapsed_sec=elapsed)
    except asyncio.TimeoutError:
        return EngineRunResult("dsa", False, out_dir=out_dir,
                               error=f"超时（>{_ENGINE_TIMEOUT}s）")


async def run_engines_parallel(
    t: NormTicker, trade_date: date, settings: Settings
) -> dict[str, EngineRunResult]:
    """并行跑启用的引擎；失败不抛异常，由上层按 single_source 降级。"""
    tasks = {}
    if settings.engine_enabled("tradingagents"):
        tasks["tradingagents"] = asyncio.create_task(run_tradingagents(t, trade_date, settings))
    if settings.engine_enabled("dsa"):
        tasks["dsa"] = asyncio.create_task(run_dsa(t, trade_date, settings))
    results = {}
    for name, task in tasks.items():
        try:
            results[name] = await task
        except Exception as exc:
            results[name] = EngineRunResult(name, False, error=str(exc))
    return results
