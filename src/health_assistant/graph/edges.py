"""LangGraph 条件路由。"""

from typing import Literal

from config.settings import get_settings
from health_assistant.graph.state import HealthState


def route_after_review(state: HealthState) -> Literal["generator", "end"]:
    """评审失败时打回生成 Agent，否则结束流程。"""
    settings = get_settings()
    review = state.get("review_result")
    retries = state.get("review_retries", 0)

    if review and review.verdict == "fail" and retries <= settings.max_review_retries:
        return "generator"
    return "end"
