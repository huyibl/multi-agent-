"""宏量营养素计算单元测试。"""

from health_assistant.schemas.user_profile import HealthGoal
from health_assistant.tools.macros import calculate_macros, calculate_protein_range


def test_protein_range_muscle_gain():
    low, high = calculate_protein_range(70, HealthGoal.MUSCLE_GAIN)
    assert low == 112  # 1.6 * 70
    assert high == 154  # 2.2 * 70


def test_calculate_macros():
    result = calculate_macros(tdee_kcal=2400, weight_kg=70, goal=HealthGoal.MUSCLE_GAIN)
    assert "protein_g" in result
    assert "carbs_g" in result
    assert "fat_g" in result
    assert result["tdee_kcal"] == 2400
