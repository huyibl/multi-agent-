"""用户档案数据模型。"""

from enum import Enum
from typing import Optional

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
        """将规划 Agent 提取的实体合并进档案。"""
        data = self.model_dump()
        mapping = {
            "height_cm": ["height_cm", "height"],
            "weight_kg": ["weight_kg", "weight"],
            "age": ["age"],
            "sex": ["sex", "gender"],
        }
        for field, keys in mapping.items():
            for key in keys:
                if key in entities and entities[key] is not None:
                    data[field] = entities[key]
                    break
        if "goal" in entities:
            goal_val = entities["goal"]
            if isinstance(goal_val, str):
                for g in HealthGoal:
                    if g.value in goal_val or goal_val in g.value:
                        data["goal"] = g
                        break
        if "activity_level" in entities:
            act = entities["activity_level"]
            if isinstance(act, str):
                for a in ActivityLevel:
                    if a.value in act:
                        data["activity_level"] = a
                        break
        return UserProfile(**data)
