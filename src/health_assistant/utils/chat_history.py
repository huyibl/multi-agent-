"""多轮对话历史格式化。"""

from __future__ import annotations

from typing import Any


def format_chat_history(
    messages: list[dict[str, Any]],
    *,
    max_turns: int = 6,
    max_chars_per_msg: int = 400,
) -> str:
    """将消息列表格式化为 Prompt 可用文本（取最近若干轮）。"""
    if not messages:
        return "（无历史对话）"

    # 每轮 = user + assistant，取最近 max_turns 轮
    trimmed = messages[-(max_turns * 2) :]
    lines: list[str] = []
    for msg in trimmed:
        role = "用户" if msg.get("role") == "user" else "教练"
        content = (msg.get("content") or "").strip().replace("\n", " ")
        if len(content) > max_chars_per_msg:
            content = content[:max_chars_per_msg] + "…"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
