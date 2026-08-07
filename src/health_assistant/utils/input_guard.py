"""用户输入信号判断：低置信闲聊 vs 健身相关。"""

from __future__ import annotations

import re
from typing import Any

_FITNESS_KEYWORDS = (
    "增肌", "减脂", "减肥", "减重", "蛋白", "热量", "卡路里", "kcal",
    "BMI", "bmi", "训练", "饮食", "膳食", "营养", "补水", "碳水", "脂肪",
    "muscle", "bulk", "lose", "calorie", "protein", "腹肌", "有氧", "力量",
    "身高", "体重", "胖子", "胖", "瘦", "运动", "锻炼", "健身房", "卧推",
    "深蹲", "跑步", "饭", "吃", "餐", "食谱", "宏量", "TDEE", "tdee",
)

_CHITCHAT_MARKERS = (
    "你是谁", "你谁", "你好", "您好", "谢谢", "感谢", "再见", "拜拜",
    "hello", "hi", "hey", "who are you", "what are you",
    "哈哈", "嘿嘿", "呵呵", "测试", "test",
)


def has_fitness_signal(text: str) -> bool:
    """文本是否含健身/营养相关信号。"""
    if not text:
        return False
    q = text.strip()
    if any(k in q for k in _FITNESS_KEYWORDS):
        return True
    if re.search(r"\d+\s*(cm|kg|岁)", q, re.I):
        return True
    if re.search(r"(身高|体重|年龄)\s*\d+", q):
        return True
    return False


def is_low_signal_query(
    query: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    """判断是否为低置信输入（闲聊/乱码/无健身信号），可走短路回复。"""
    q = (query or "").strip()
    if not q:
        return True

    if has_fitness_signal(q):
        return False

    # 历史里刚在聊健身且当前像短追问 → 不算低信号
    history = history or []
    recent_user = " ".join(
        m.get("content", "") for m in history[-4:] if m.get("role") == "user"
    )
    if has_fitness_signal(recent_user) and len(q) <= 20:
        return False

    ql = q.lower()
    if any(m in q or m in ql for m in _CHITCHAT_MARKERS):
        return True

    # 无数字、无健身词、较短 → 当作随便输入
    if len(q) <= 40 and not any(ch.isdigit() for ch in q):
        return True

    # 纯符号/乱码
    if re.fullmatch(r"[\W_]+", q, flags=re.UNICODE):
        return True

    return False


def chitchat_reply(query: str) -> str:
    """低信号输入的固定友好回复（不走检索/计算）。"""
    q = (query or "").strip()
    if any(m in q for m in ("你是谁", "你谁", "who are you", "what are you")):
        return (
            "我是 **AI 健身教练**：可以帮你看蛋白质、热量、训练与饮食方向。\n\n"
            "直接说出身高体重和目标就行，例如：\n"
            "「我身高172体重70，想增肌，每天吃多少蛋白？」\n\n"
            "> 仅供健身营养参考，不构成医疗建议。"
        )
    if any(m in q.lower() for m in ("你好", "您好", "hello", "hi", "hey")):
        return (
            "你好！我是 AI 健身教练。\n\n"
            "可以说身高、体重和目标（增肌/减脂），我来给可执行的饮食与训练建议。\n\n"
            "> 仅供健身营养参考，不构成医疗建议。"
        )
    return (
        "我主要回答健身和营养问题（蛋白质、热量、训练安排等）。\n\n"
        "你可以这样问：\n"
        "- 我身高172体重70，想增肌，蛋白怎么吃？\n"
        "- 减脂期一天大概多少热量？\n\n"
        "如果说出身高体重，我还能帮你算 BMI / 蛋白质区间。\n\n"
        "> 仅供健身营养参考，不构成医疗建议。"
    )
