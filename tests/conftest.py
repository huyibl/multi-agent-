"""pytest 测试夹具。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from health_assistant.schemas.user_profile import ActivityLevel, HealthGoal, UserProfile


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        height_cm=172,
        weight_kg=70,
        age=28,
        sex="male",
        activity_level=ActivityLevel.MODERATE,
        goal=HealthGoal.MUSCLE_GAIN,
    )
