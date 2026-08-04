"""宏量营养素计算工具。"""

from health_assistant.schemas.user_profile import HealthGoal

# 按健康目标划分的蛋白质范围（g/kg 体重，基于常见证据默认值）
PROTEIN_RANGES = {
    HealthGoal.LOSE_WEIGHT: (1.2, 1.6),
    HealthGoal.MAINTAIN: (0.8, 1.2),
    HealthGoal.BULK: (1.6, 2.2),
    HealthGoal.MUSCLE_GAIN: (1.6, 2.2),
    HealthGoal.GENERAL_HEALTH: (0.8, 1.2),
}


def calculate_protein_range(
    weight_kg: float,
    goal: HealthGoal = HealthGoal.GENERAL_HEALTH,
) -> tuple[float, float]:
    """返回每日蛋白质摄入范围（克）。"""
    low, high = PROTEIN_RANGES.get(goal, (0.8, 1.2))
    return (round(weight_kg * low), round(weight_kg * high))


def calculate_macros(
    tdee_kcal: float,
    weight_kg: float,
    goal: HealthGoal = HealthGoal.GENERAL_HEALTH,
    protein_per_kg: tuple[float, float] | None = None,
) -> dict[str, float]:
    """根据 TDEE 和健康目标计算宏量营养素目标。"""
    if protein_per_kg is None:
        protein_per_kg = PROTEIN_RANGES.get(goal, (0.8, 1.2))
    protein_g = round(weight_kg * sum(protein_per_kg) / 2)
    protein_kcal = protein_g * 4

    if goal in (HealthGoal.BULK, HealthGoal.MUSCLE_GAIN):
        fat_ratio = 0.25
    elif goal == HealthGoal.LOSE_WEIGHT:
        fat_ratio = 0.30
    else:
        fat_ratio = 0.28

    fat_kcal = tdee_kcal * fat_ratio
    fat_g = round(fat_kcal / 9)
    carbs_kcal = max(tdee_kcal - protein_kcal - fat_kcal, 0)
    carbs_g = round(carbs_kcal / 4)

    return {
        "protein_g": protein_g,
        "protein_range_g": calculate_protein_range(weight_kg, goal),
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "tdee_kcal": tdee_kcal,
    }
