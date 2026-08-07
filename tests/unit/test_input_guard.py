"""输入分流与实体清洗单元测试。"""

from health_assistant.schemas.user_profile import UserProfile, sanitize_entities
from health_assistant.utils.input_guard import has_fitness_signal, is_low_signal_query


def test_sanitize_drops_absurd_weight():
    clean = sanitize_entities({"weight_kg": 16666.5, "height_cm": 172})
    assert "weight_kg" not in clean
    assert clean["height_cm"] == 172


def test_merge_never_raises_on_absurd_entities():
    profile = UserProfile(height_cm=170, weight_kg=70)
    merged = profile.merge_from_entities({"weight_kg": 16666.5, "height_cm": 9999})
    assert merged.weight_kg == 70
    assert merged.height_cm == 170


def test_low_signal_chitchat():
    assert is_low_signal_query("你谁")
    assert is_low_signal_query("你好")
    assert is_low_signal_query("asdfgh")
    assert not is_low_signal_query("我身高172体重70想增肌")
    assert not is_low_signal_query("不是我是胖子，不活动的")
    assert has_fitness_signal("不是我是胖子，不活动的")
