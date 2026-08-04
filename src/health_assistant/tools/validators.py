"""健康计算输入校验。"""


def validate_height(height_cm: float) -> None:
    if not 100 <= height_cm <= 250:
        raise ValueError(f"身高必须在 100-250 cm 之间，当前为 {height_cm}")


def validate_weight(weight_kg: float) -> None:
    if not 30 <= weight_kg <= 300:
        raise ValueError(f"体重必须在 30-300 kg 之间，当前为 {weight_kg}")


def validate_age(age: int) -> None:
    if not 10 <= age <= 120:
        raise ValueError(f"年龄必须在 10-120 岁之间，当前为 {age}")


def validate_protein_in_range(
    stated_protein: float,
    expected_range: tuple[float, float],
    tolerance: float = 0.15,
) -> bool:
    """检查声明的蛋白质数值是否在预期范围内（含容差）。"""
    low, high = expected_range
    margin = (high - low) * tolerance
    return (low - margin) <= stated_protein <= (high + margin)
