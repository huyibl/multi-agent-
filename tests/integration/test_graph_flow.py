"""LangGraph 工作流集成测试。"""

from health_assistant.schemas.user_profile import UserProfile
from health_assistant.services.chat_service import ChatService


def test_graph_flow_without_llm(sample_profile: UserProfile):
    """端到端流程测试（使用规则兜底，无需 API Key）。"""
    service = ChatService()
    query = "我身高172，体重70，想增肌，每天吃多少蛋白质？"
    response = service.ask(query, profile=sample_profile)

    assert response.answer
    assert response.calculations is not None
    assert response.calculations.bmi == 23.7
    assert response.calculations.protein_range_g == (112, 154)
    assert response.review_status in ("pass", "fail")
