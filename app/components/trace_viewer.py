"""Agent 思考过程展示组件。"""

from __future__ import annotations

from typing import Any

import streamlit as st


def _status_icon(status: str) -> str:
    """将步骤状态映射为展示用图标。"""
    return {"running": "⏳", "done": "✅", "error": "❌"}.get(status, "•")


def render_trace_viewer(trace: list[dict[str, Any]] | None) -> None:
    """在侧边栏或面板中展示 Agent 执行轨迹。"""
    st.subheader("Agent 思考过程")
    if not trace:
        st.caption("提问后将逐步展示规划 → 检索/计算 → 生成 → 评审。")
        return

    for event in trace:
        icon = _status_icon(event.get("status", "done"))
        title = event.get("title", event.get("step", ""))
        used_llm = event.get("used_llm")
        latency = event.get("latency_ms")
        badges = []
        if used_llm is True:
            badges.append("LLM")
        elif used_llm is False:
            badges.append("规则/工具")
        if latency is not None:
            badges.append(f"{latency:.0f} ms")
        badge_text = " · ".join(badges)
        label = f"{icon} {title}" + (f"  `{badge_text}`" if badge_text else "")

        with st.expander(label, expanded=event.get("status") == "running"):
            st.markdown(event.get("detail") or "—")
            data = event.get("data") or {}
            if data.get("intent"):
                st.caption(f"意图: `{data['intent']}`")
            if data.get("retrieval_queries"):
                st.caption("检索词: " + ", ".join(data["retrieval_queries"][:3]))
            if data.get("sources"):
                st.caption("来源: " + ", ".join(data["sources"][:5]))


def render_live_trace(placeholder, trace: list[dict[str, Any]]) -> None:
    """在占位符中刷新思考过程（流式过程中调用）。"""
    with placeholder.container():
        render_trace_viewer(trace)
