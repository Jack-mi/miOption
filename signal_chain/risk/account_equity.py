"""只读获取 Futu REAL 账户权益，作为单标的敞口分母。

美股优先用综合账户总资产折成美元。汇率用账户自己的计价：
总资产与港币资产的差额除以美元资产，并且只在没有其他币种、汇率落在
7.0–8.3 时采用。没有可靠汇率时仍用美元现金，并注明未计入其他币种。
港股仍用港币资产。

本模块通过 runtime/.venv 子进程调用 futu-api，避免污染 signal_chain 环境。
失败返回 None，由风控显式告警但不阻断研究链路。
"""

from __future__ import annotations

import json
import subprocess

from ..config import REPO_ROOT, require_runtime_python, Settings

_CASH_NOTE = "仅美元现金，未计入其他币种"
_FX_LO = 7.0
_FX_HI = 8.3


def _f(data: dict, key: str) -> float | None:
    try:
        value = float(data[key])
    except (KeyError, TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def equity_from_accinfo(market: str, data: dict) -> dict | None:
    """把 accinfo 行收成风控分母。纯函数，方便不连 OpenD 做测试。"""
    source = "futu_real_accinfo"
    if market == "HK":
        hkd = _f(data, "hkd_assets")
        if hkd is None or hkd <= 0:
            return None
        return {
            "value": hkd,
            "currency": "HKD",
            "field": "hkd_assets",
            "source": source,
            "original_value": hkd,
            "original_currency": "HKD",
            "fx_rate": None,
            "fx_source": None,
            "note": None,
        }
    if market != "US":
        return None
    usd = _f(data, "usd_assets")
    total = _f(data, "total_assets")
    hkd = _f(data, "hkd_assets")
    other = _f(data, "other_assets") or 0.0
    currency = str(data.get("currency") or "")
    if currency == "USD" and total is not None and total > 0:
        return {
            "value": total,
            "currency": "USD",
            "field": "total_assets",
            "source": source,
            "original_value": total,
            "original_currency": "USD",
            "fx_rate": 1.0,
            "fx_source": "account_currency",
            "note": None,
        }
    if (
        currency == "HKD"
        and total is not None
        and hkd is not None
        and usd is not None
        and usd > 0
        and other == 0
        and total > hkd
    ):
        fx = (total - hkd) / usd
        if _FX_LO <= fx <= _FX_HI:
            return {
                "value": total / fx,
                "currency": "USD",
                "field": "total_assets",
                "source": source,
                "original_value": total,
                "original_currency": "HKD",
                "fx_rate": fx,
                "fx_source": "futu_accinfo_implied",
                "note": None,
            }
    if usd is None or usd <= 0:
        return None
    return {
        "value": usd,
        "currency": "USD",
        "field": "usd_assets",
        "source": source,
        "original_value": usd,
        "original_currency": "USD",
        "fx_rate": None,
        "fx_source": None,
        "note": _CASH_NOTE,
    }


def read_account_equity(market: str, settings: Settings) -> dict | None:
    if market not in {"US", "HK"}:
        return None
    cfg = settings.chain
    try:
        runtime_py = require_runtime_python()
    except FileNotFoundError:
        return None
    cmd = [
        str(runtime_py), "-m", "signal_chain.risk.account_equity_bridge",
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
    except json.JSONDecodeError:
        return None
    return equity_from_accinfo(market, data)
