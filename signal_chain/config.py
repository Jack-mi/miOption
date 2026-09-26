"""配置加载：config.yaml + 仓库路径常量 + 标的代码归一。无 LLM。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

SIGNALS_DIR = REPO_ROOT / "signals"
CHAINS_DIR = REPO_ROOT / "chains"
REPORTS_DIR = REPO_ROOT / "reports"
RUNS_DIR = REPO_ROOT / "runs"
# futu-api 只装在这个解释器里。缺失就报这条路径，不用当前进程的 Python 顶上。
RUNTIME_VENV_PY = REPO_ROOT / "runtime" / ".venv" / "bin" / "python"


def require_runtime_python() -> Path:
    if not RUNTIME_VENV_PY.is_file():
        raise FileNotFoundError(
            f"富途桥需要 {RUNTIME_VENV_PY}，不会改用当前解释器"
        )
    return RUNTIME_VENV_PY


def _load_yaml() -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any] = field(default_factory=_load_yaml)

    @property
    def models(self) -> dict[str, str]:
        return dict(self.raw["models"])

    @property
    def watchlist(self) -> list[str]:
        return list(self.raw.get("watchlist", []))

    @property
    def synthesis(self) -> dict[str, Any]:
        return dict(self.raw["synthesis"])

    @property
    def risk(self) -> dict[str, Any]:
        return dict(self.raw["risk"])

    @property
    def chain(self) -> dict[str, Any]:
        return dict(self.raw["chain"])

def load_settings() -> Settings:
    return Settings()


def ensure_dirs() -> None:
    for d in (SIGNALS_DIR, CHAINS_DIR, REPORTS_DIR, RUNS_DIR):
        d.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class NormTicker:
    """归一格式 US.AAPL / HK.00700 / CN.600519。"""

    market: str  # US | HK | CN
    code: str

    @property
    def canonical(self) -> str:
        return f"{self.market}.{self.code}"

    @property
    def ta_format(self) -> str:
        """Yahoo Finance 格式：AAPL / 0700.HK / 600519.SS。"""
        if self.market == "HK":
            return f"{str(int(self.code)).zfill(4)}.HK"  # Yahoo 用 4 位港股代码
        if self.market == "CN":
            suffix = ".SS" if self.code.startswith("6") else ".SZ"
            return f"{self.code}{suffix}"
        return self.code

    @property
    def futu_format(self) -> str:
        """Futu OpenD 格式：US.AAPL / HK.00700。"""
        return self.canonical


def parse_ticker(text: str) -> NormTicker:
    t = text.strip().upper()
    if t.startswith(("US.", "HK.", "CN.")):
        market, code = t.split(".", 1)
        if market == "HK":
            code = code.zfill(5)
        return NormTicker(market, code)
    if t.endswith(".HK"):
        return NormTicker("HK", t[:-3].zfill(5))
    if t.startswith("HK") and t[2:].isdigit():
        return NormTicker("HK", t[2:].zfill(5))
    if t.endswith((".SS", ".SZ")):
        return NormTicker("CN", t[:-3])
    if t.isdigit() and len(t) == 6:
        return NormTicker("CN", t)
    return NormTicker("US", t)
