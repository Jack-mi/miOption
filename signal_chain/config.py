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
VENDOR_DIR = REPO_ROOT / "vendor"
TA_DIR = VENDOR_DIR / "TradingAgents"
DSA_DIR = VENDOR_DIR / "daily_stock_analysis"
TA_VENV_PY = TA_DIR / ".venv" / "bin" / "python"
DSA_VENV_PY = DSA_DIR / ".venv" / "bin" / "python"
RUNTIME_VENV_PY = REPO_ROOT / "runtime" / ".venv" / "bin" / "python"
VENDOR_LOCK = REPO_ROOT / "vendor.lock.json"


def _load_yaml() -> dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any] = field(default_factory=_load_yaml)

    @property
    def router_base_url(self) -> str:
        return self.raw["router"]["base_url"]

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

    def engine_enabled(self, name: str) -> bool:
        return bool(self.raw.get("engines", {}).get(name, {}).get("enabled", False))

    def ta_results_dir(self) -> Path:
        rel = self.raw["engines"]["tradingagents"].get("results_dir", "runs/ta")
        return REPO_ROOT / rel


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
        """TradingAgents/Yahoo 格式：AAPL / 0700.HK / 600519.SS。"""
        if self.market == "HK":
            return f"{str(int(self.code)).zfill(4)}.HK"  # Yahoo 用 4 位港股代码
        if self.market == "CN":
            suffix = ".SS" if self.code.startswith("6") else ".SZ"
            return f"{self.code}{suffix}"
        return self.code

    @property
    def dsa_format(self) -> str:
        """DSA 格式：AAPL / hk00700 / 600519。"""
        if self.market == "HK":
            return f"hk{self.code}"
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
