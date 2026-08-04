"""使用 Mifflin-St Jeor 公式计算 TDEE。"""

from health_assistant.schemas.user_profile import ActivityLevel
from health_assistant.tools.validators import validate_age, validate_height, validate_weight

ACTIVITY_MULTIPLIERS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor 基础代谢率（BMR）。"""
    validate_weight(weight_kg)
    validate_height(height_cm)
    validate_age(age)
    sex = (sex or "male").lower()
    if sex in ("female", "f", "女"):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity_level: ActivityLevel = ActivityLevel.MODERATE,
) -> float:
    """每日总能量消耗（TDEE）。"""
    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * multiplier)
