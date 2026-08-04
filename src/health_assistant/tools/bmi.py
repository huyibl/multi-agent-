"""BMI 计算工具。"""

from health_assistant.tools.validators import validate_height, validate_weight


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """计算身体质量指数（BMI）。"""
    validate_height(height_cm)
    validate_weight(weight_kg)
    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def bmi_category(bmi: float) -> str:
    """返回 BMI 分类标签。"""
    if bmi < 18.5:
        return "underweight"
    if bmi < 24:
        return "normal"
    if bmi < 28:
        return "overweight"
    return "obese"
