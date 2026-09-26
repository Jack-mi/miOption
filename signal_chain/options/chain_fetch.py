"""取链编排：Futu OpenD 主源（港美），美股失败时降级 yfinance。确定性代码。"""

from __future__ import annotations

import json
import subprocess

from ..config import REPO_ROOT, NormTicker, require_runtime_python, Settings
from ..schema import ChainSnapshot
from .yfinance_chain import fetch_chain_yfinance

_BRIDGE_TIMEOUT = 120


def _fetch_chain_futu(t: NormTicker, settings: Settings) -> ChainSnapshot:
    cfg = settings.chain
    cmd = [
        str(require_runtime_python()), "-m", "signal_chain.options.futu_bridge",
        t.futu_format, str(cfg["expiry_window_days"]),
        str(cfg["futu_opend_host"]), str(cfg["futu_opend_port"]),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_BRIDGE_TIMEOUT,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"futu bridge failed(rc={proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    json_line = next(
        (ln for ln in reversed(proc.stdout.splitlines()) if ln.strip().startswith("{")),
        None,
    )
    if json_line is None:
        raise RuntimeError(f"futu bridge 无 JSON 输出: {proc.stdout[:200]} {proc.stderr[:200]}")
    data = json.loads(json_line)
    return ChainSnapshot.model_validate(data)


def fetch_chain(t: NormTicker, settings: Settings) -> ChainSnapshot:
    """主源 Futu；美股 Futu 失败时降级 yfinance（降级结果 degraded=True）。"""
    try:
        return _fetch_chain_futu(t, settings)
    except Exception as exc:
        if t.market != "US":
            raise
        snap = fetch_chain_yfinance(
            t.ta_format, t.market, t.canonical, settings.chain["expiry_window_days"]
        )
        snap.degraded = True
        snap.notes = f"Futu 主源失败（{exc}），已降级 yfinance；数据有延迟"
        return snap
