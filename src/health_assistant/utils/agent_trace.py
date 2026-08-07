"""Agent 思考过程 / 执行轨迹工具。"""

from __future__ import annotations

import time
from typing import Any, Optional


def new_trace() -> list[dict[str, Any]]:
    """创建空的 Agent 执行轨迹列表。"""
    return []


def append_trace(
    trace: list[dict[str, Any]],
    step: str,
    title: str,
    status: str = "done",
    detail: str = "",
    used_llm: Optional[bool] = None,
    latency_ms: Optional[float] = None,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """追加一步轨迹事件并返回该事件（供 UI 实时展示）。"""
    event = {
        "step": step,
        "title": title,
        "status": status,
        "detail": detail,
        "used_llm": used_llm,
        "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        "data": data or {},
        "ts": time.time(),
    }
    trace.append(event)
    return event


class StepTimer:
    """简单步骤计时器。"""

    def __init__(self):
        self._start = time.perf_counter()

    def ms(self) -> float:
        """自创建以来经过的毫秒数。"""
        return (time.perf_counter() - self._start) * 1000
