"""对话服务：多 Agent 工作流入口。"""

from typing import Optional

from config.settings import get_settings
from health_assistant.graph.workflow import build_workflow
from health_assistant.schemas.response import HealthResponse
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.citation_formatter import format_citations


class ChatService:
    """通过 LangGraph 编排健康问答。"""

    def __init__(self):
        self.settings = get_settings()
        self.settings.configure_tracing()
        self.graph = build_workflow()

    def ask(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
    ) -> HealthResponse:
        """处理用户查询并返回结构化响应。"""
        profile = profile or UserProfile()
        initial_state = {
            "query": query,
            "profile": profile,
            "review_retries": 0,
            "review_feedback": "",
            "metadata": {},
        }

        final_state = self.graph.invoke(initial_state)

        gen = final_state.get("generator_output")
        review = final_state.get("review_result")
        chunks = final_state.get("retrieved_chunks", [])
        calculations = final_state.get("calculation_results")
        plan = final_state.get("plan")

        answer = gen.answer if gen else "无法生成回答，请检查配置。"
        citations = gen.citations if gen and gen.citations else format_citations(chunks)

        return HealthResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks=chunks,
            calculations=calculations,
            review_status=review.verdict if review else "pass",
            review_feedback=review.feedback if review else "",
            plan=plan.model_dump() if plan else {},
            metadata=final_state.get("metadata", {}),
        )
