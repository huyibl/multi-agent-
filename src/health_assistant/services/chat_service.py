"""对话服务：多 Agent 工作流入口。"""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from config.settings import get_settings
from health_assistant.agents.calculator import CalculatorAgent
from health_assistant.agents.generator import GeneratorAgent
from health_assistant.agents.planner import PlannerAgent
from health_assistant.agents.retriever import RetrieverAgent
from health_assistant.agents.reviewer import ReviewerAgent
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
        self._last_response: Optional[HealthResponse] = None

    @property
    def last_response(self) -> Optional[HealthResponse]:
        return self._last_response

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
            "metadata": {"llm_calls": 0},
        }

        final_state = self.graph.invoke(initial_state)
        response = self._build_response(final_state)
        self._last_response = response
        return response

    def ask_stream(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
    ) -> Iterator[str]:
        """流式生成：规划 → 并行检索/计算 → 流式 Generator → 规则评审。"""
        profile = profile or UserProfile()
        llm_calls = 0

        planner = PlannerAgent()
        rule_plan = planner._rule_based_plan(query, profile)
        if planner._should_use_llm(query, rule_plan):
            llm_calls += 1
        plan = planner.run(query=query, profile=profile)
        profile = profile.merge_from_entities(plan.entities)

        retriever = RetrieverAgent()
        calculator = CalculatorAgent()
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_r = pool.submit(retriever.run, query, plan)
            fut_c = pool.submit(calculator.run, profile, plan)
            chunks = fut_r.result()
            calculations = fut_c.result()

        generator = GeneratorAgent()
        reviewer = ReviewerAgent()
        review_feedback = ""
        review_retries = 0
        max_retries = self.settings.max_review_retries

        while True:
            parts: list[str] = []
            for token in generator.stream_tokens(
                query, plan, chunks, calculations, review_feedback
            ):
                parts.append(token)
                yield token

            raw = "".join(parts)
            if generator.settings.deepseek_api_key:
                llm_calls += 1
                gen_output = generator.output_from_stream(raw, chunks)
            else:
                gen_output = generator.run(
                    query, plan, chunks, calculations, review_feedback
                )

            review = reviewer.run(query, gen_output.answer, chunks, calculations)
            if reviewer.settings.reviewer_use_llm == "always" and reviewer.settings.deepseek_api_key:
                llm_calls += 1

            if review.verdict == "pass" or review_retries >= max_retries:
                citations = gen_output.citations or format_citations(chunks)
                self._last_response = HealthResponse(
                    answer=gen_output.answer,
                    citations=citations,
                    retrieved_chunks=chunks,
                    calculations=calculations,
                    review_status=review.verdict,
                    review_feedback=review.feedback,
                    plan=plan.model_dump(),
                    metadata={"llm_calls": llm_calls},
                )
                break

            review_feedback = review.feedback
            review_retries += 1

    def _build_response(self, final_state: dict) -> HealthResponse:
        gen = final_state.get("generator_output")
        review = final_state.get("review_result")
        chunks = final_state.get("retrieved_chunks", [])
        calculations = final_state.get("calculation_results")
        plan = final_state.get("plan")
        meta = final_state.get("metadata") or {}

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
            metadata=meta,
        )
