"""BMI 计算单元测试。"""

import pytest

from health_assistant.tools.bmi import bmi_category, calculate_bmi


def test_calculate_bmi():
    assert calculate_bmi(172, 70) == 23.7


def test_bmi_category_normal():
    assert bmi_category(22.0) == "normal"


def test_bmi_category_overweight():
    assert bmi_category(26.0) == "overweight"


def test_invalid_height():
    with pytest.raises(ValueError):
        calculate_bmi(50, 70)
