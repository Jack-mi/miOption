"""适配器基座：引擎原始产物 -> RawBundle（确定性字段 + 报告文本）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..schema import Direction


@dataclass
class RawBundle:
    """引擎原始输出的归一化载体。确定性字段在此算好，文本留给抽取 agent。"""

    engine: str                      # 引擎标识
    ticker: str                      # 归一格式
    market: str
    as_of: date
    report_ref: str                  # 原始报告路径
    direction: Direction | None      # None = 信号作废
    conviction: float = 0.0
    data_sources: list[str] = field(default_factory=list)
    engine_version: str | None = None
    llm_model: str | None = None
    texts: dict[str, str] = field(default_factory=dict)   # section -> content
    meta: dict = field(default_factory=dict)
    data_status: str = "actionable"          # actionable / insufficient_data
    data_gaps: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.direction is not None
