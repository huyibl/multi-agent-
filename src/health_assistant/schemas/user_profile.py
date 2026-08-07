"""用户档案数据模型。"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ActivityLevel(str, Enum):
    """日常活动水平（用于 TDEE 系数）。"""

    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class HealthGoal(str, Enum):
    """健身/营养目标（影响蛋白质与宏量配比）。"""

    LOSE_WEIGHT = "lose_weight"
    MAINTAIN = "maintain"
    BULK = "bulk"
    MUSCLE_GAIN = "muscle_gain"
    GENERAL_HEALTH = "general_health"


# 与 Field 约束保持一致；脏实体统一按此清洗
HEIGHT_RANGE = (100.0, 250.0)
WEIGHT_RANGE = (30.0, 300.0)
AGE_RANGE = (10, 120)


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def sanitize_entities(entities: Optional[dict[str, Any]]) -> dict[str, Any]:
    """清洗 Planner/LLM 产出的实体：非法类型或超范围字段直接丢弃。"""
    if not entities:
        return {}
    clean: dict[str, Any] = {}

    for key in ("height_cm", "height"):
        if key not in entities or entities[key] is None:
            continue
        val = _to_float(entities[key])
        if val is not None and HEIGHT_RANGE[0] <= val <= HEIGHT_RANGE[1]:
            clean["height_cm"] = val
        break

    for key in ("weight_kg", "weight"):
        if key not in entities or entities[key] is None:
            continue
        val = _to_float(entities[key])
        if val is not None and WEIGHT_RANGE[0] <= val <= WEIGHT_RANGE[1]:
            clean["weight_kg"] = val
        break

    if entities.get("age") is not None:
        age = _to_int(entities["age"])
        if age is not None and AGE_RANGE[0] <= age <= AGE_RANGE[1]:
            clean["age"] = age

    sex = entities.get("sex") or entities.get("gender")
    if isinstance(sex, str):
        s = sex.strip().lower()
        if s in {"male", "m", "男", "男性"}:
            clean["sex"] = "male"
        elif s in {"female", "f", "女", "女性"}:
            clean["sex"] = "female"

    if "goal" in entities and entities["goal"] is not None:
        clean["goal"] = entities["goal"]
    if "activity_level" in entities and entities["activity_level"] is not None:
        clean["activity_level"] = entities["activity_level"]

    return clean


class UserProfile(BaseModel):
    """用于个性化计算的用户健康档案。"""

    height_cm: Optional[float] = Field(default=None, ge=100, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=30, le=300)
    age: Optional[int] = Field(default=None, ge=10, le=120)
    sex: Optional[str] = Field(default=None, description="male 或 female")
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    goal: HealthGoal = HealthGoal.GENERAL_HEALTH

    def to_context(self) -> dict:
        """序列化为 Agent Prompt 可用的字典。"""
        return {
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "age": self.age,
            "sex": self.sex,
            "activity_level": self.activity_level.value,
            "goal": self.goal.value,
        }

    def merge_from_entities(self, entities: dict) -> "UserProfile":
        """将规划 Agent 提取的实体合并进档案。

        非法/离谱数值会被丢弃；合并失败时返回原档案，绝不抛到 UI。
        """
        clean = sanitize_entities(entities)
        data = self.model_dump()
        for field in ("height_cm", "weight_kg", "age", "sex"):
            if field in clean:
                data[field] = clean[field]

        if "goal" in clean:
            goal_val = clean["goal"]
            if isinstance(goal_val, str):
                for g in HealthGoal:
                    if g.value in goal_val or goal_val in g.value:
                        data["goal"] = g
                        break
            elif isinstance(goal_val, HealthGoal):
                data["goal"] = goal_val

        if "activity_level" in clean:
            act = clean["activity_level"]
            if isinstance(act, str):
                # 自然语言弱映射
                text = act.lower()
                if any(k in text for k in ("不活动", "久坐", "sedentary", "躺")):
                    data["activity_level"] = ActivityLevel.SEDENTARY
                elif any(k in text for k in ("很少", "轻", "light")):
                    data["activity_level"] = ActivityLevel.LIGHT
                else:
                    for a in ActivityLevel:
                        if a.value in text:
                            data["activity_level"] = a
                            break
            elif isinstance(act, ActivityLevel):
                data["activity_level"] = act

        try:
            return UserProfile(**data)
        except Exception:
            return self.model_copy()
