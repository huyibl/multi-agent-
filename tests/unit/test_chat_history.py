"""多轮历史与追问规划测试。"""

from health_assistant.agents.planner import PlannerAgent
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.chat_history import format_chat_history


def test_format_chat_history():
    text = format_chat_history(
        [
            {"role": "user", "content": "我身高172体重70想增肌"},
            {"role": "assistant", "content": "建议蛋白质112-154克"},
            {"role": "user", "content": "那碳水呢"},
        ]
    )
    assert "用户" in text
    assert "碳水" in text


def test_followup_reuses_entities_from_history():
    agent = PlannerAgent()
    profile = UserProfile()
    history = [
        {"role": "user", "content": "我身高172，体重70，想增肌，每天吃多少蛋白质？"},
        {"role": "assistant", "content": "建议蛋白质 112～154 克。"},
    ]
    plan = agent.run("那碳水大概吃多少？", profile=profile, history=history)
    assert plan.entities.get("height_cm") == 172
    assert plan.entities.get("weight_kg") == 70
    assert plan.intent in ("muscle_gain_nutrition", "calorie_nutrition", "general_fitness")
