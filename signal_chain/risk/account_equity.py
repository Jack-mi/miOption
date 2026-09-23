"""只读获取 Futu REAL 账户的标的同币种权益。

Futu 的 accinfo_query 返回综合账户及多币种字段。风控按标的市场取：
- US -> usd_assets（USD）
- HK -> hkd_assets（HKD）

本模块通过 runtime/.venv 子进程调用 futu-api，避免污染 signal_chain 环境。
失败返回 None，由风控显式告警但不阻断研究链路。
"""

from __future__ import annotations

import json
import subprocess

from ..config import REPO_ROOT, RUNTIME_VENV_PY, Settings


def read_account_equity(market: str, settings: Settings) -> dict | None:
    if market not in {"US", "HK"}:
        return None
    cfg = settings.chain
    cmd = [
        str(RUNTIME_VENV_PY), "-m", "signal_chain.risk.account_equity_bridge",
        market, str(cfg["futu_opend_host"]), str(cfg["futu_opend_port"]),
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    line = next(
        (ln for ln in reversed(proc.stdout.splitlines()) if ln.strip().startswith("{")),
        None,
    )
    if line is None:
        return None
    try:
        data = json.loads(line)
        value = float(data["value"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if value <= 0:
        return None
    return {
        "value": value,
        "currency": str(data["currency"]),
        "field": str(data["field"]),
        "source": "futu_real_accinfo",
    }
