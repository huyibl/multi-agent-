"""对话服务：多 Agent 工作流入口（支持多轮上下文与会话档案）。"""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from config.settings import get_settings
from health_assistant.agents.calculator import CalculatorAgent
from health_assistant.agents.generator import GeneratorAgent
from health_assistant.agents.planner import PlannerAgent
from health_assistant.agents.retriever import RetrieverAgent
from health_assistant.agents.reviewer import ReviewerAgent
from health_assistant.graph.workflow import build_workflow
from health_assistant.schemas.response import HealthResponse
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.agent_trace import StepTimer, append_trace, new_trace
from health_assistant.utils.citation_formatter import format_citations


class ChatService:
    """事件流编排健身问答（拓扑与 LangGraph ``build_workflow`` 同构）。"""

    def __init__(self):
        """加载配置并启用追踪；预编译图便于扩展/可视化。"""
        self.settings = get_settings()
        self.settings.configure_tracing()
        # 在线路径走 ask_events；graph 供集成测试与后续 checkpoint 使用
        self.graph = build_workflow()
        self._last_response: Optional[HealthResponse] = None

    @property
    def last_response(self) -> Optional[HealthResponse]:
        """最近一次 ``ask`` / ``ask_events`` 完成的响应。"""
        return self._last_response

    def ask(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> HealthResponse:
        """同步问答：消费事件流并返回最终 ``HealthResponse``。"""
        response: Optional[HealthResponse] = None
        for event in self.ask_events(query, profile=profile, history=history):
            if event.get("type") == "done":
                response = event["response"]
        assert response is not None
        return response

    def ask_stream(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """仅 yield 生成阶段的文本 Token。"""
        for event in self.ask_events(query, profile=profile, history=history):
            if event.get("type") == "token":
                yield event["text"]

    def ask_events(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> Iterator[dict[str, Any]]:
        """编排多 Agent 流水线并产出 UI 事件。

        Yields:
            ``trace`` / ``token`` / ``profile`` / ``done`` 事件字典。
        """
        profile = profile or UserProfile()
        history = history or []
        llm_calls = 0
        trace = new_trace()

        yield {"type": "trace", "event": append_trace(
            trace, "planner", "规划 Agent", status="running",
            detail="结合历史对话识别意图、更新用户档案…",
        )}
        timer = StepTimer()
        planner = PlannerAgent()
        rule_plan = planner._rule_based_plan(query, profile, history)
        used_llm = planner._should_use_llm(query, rule_plan, history)
        if used_llm:
            llm_calls += 1
        plan = planner.run(query=query, profile=profile, history=history)
        profile = profile.merge_from_entities(plan.entities)
        yield {"type": "profile", "profile": profile}
        yield {"type": "trace", "event": append_trace(
            trace, "planner", "规划 Agent",
            status="done",
            used_llm=used_llm,
            latency_ms=timer.ms(),
            detail=(
                f"intent={plan.intent} | "
                f"{'调用 LLM' if used_llm else '规则短路'} | "
                f"档案: 身高={profile.height_cm or '未知'} "
                f"体重={profile.weight_kg or '未知'} "
                f"目标={profile.goal.value}"
            ),
            data={
                "intent": plan.intent,
                "entities": plan.entities,
                "profile": profile.to_context(),
                "retrieval_queries": plan.retrieval_queries,
            },
        )}

        yield {"type": "trace", "event": append_trace(
            trace, "parallel_fetch", "检索 ∥ 计算", status="running",
            detail="并行执行规范检索与营养计算…",
        )}
        timer = StepTimer()
        retriever = RetrieverAgent()
        calculator = CalculatorAgent()
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_r = pool.submit(retriever.run, query, plan)
            fut_c = pool.submit(calculator.run, profile, plan)
            chunks = fut_r.result()
            calculations = fut_c.result()

        sources = [c.source for c in chunks[:5]]
        calc_bits = []
        if calculations and calculations.bmi:
            calc_bits.append(f"BMI={calculations.bmi}")
        if calculations and calculations.protein_range_g:
            lo, hi = calculations.protein_range_g
            calc_bits.append(f"蛋白={lo}-{hi}g")
        if calculations and calculations.tdee_kcal:
            calc_bits.append(f"TDEE={calculations.tdee_kcal}")
        yield {"type": "trace", "event": append_trace(
            trace, "parallel_fetch", "检索 ∥ 计算",
            status="done",
            used_llm=False,
            latency_ms=timer.ms(),
            detail=(
                f"命中 {len(chunks)} 块 | 来源: {', '.join(sources) or '无'} | "
                f"{'; '.join(calc_bits) or '暂无计算（缺少身高体重时可追问补充）'}"
            ),
            data={
                "chunk_count": len(chunks),
                "sources": sources,
                "calculations": calculations.model_dump() if calculations else {},
            },
        )}

        generator = GeneratorAgent()
        reviewer = ReviewerAgent()
        review_feedback = ""
        review_retries = 0
        max_retries = self.settings.max_review_retries

        while True:
            yield {"type": "trace", "event": append_trace(
                trace, "generator", "生成 Agent", status="running",
                detail="结合历史对话与计算结果生成教练建议…",
                used_llm=bool(generator.settings.deepseek_api_key),
            )}
            timer = StepTimer()
            parts: list[str] = []
            for token in generator.stream_tokens(
                query, plan, chunks, calculations, review_feedback,
                profile=profile, history=history,
            ):
                parts.append(token)
                yield {"type": "token", "text": token}

            raw = "".join(parts)
            if generator.settings.deepseek_api_key:
                llm_calls += 1
                gen_output = generator.output_from_stream(raw, chunks)
            else:
                gen_output = generator.run(
                    query, plan, chunks, calculations, review_feedback,
                    profile=profile, history=history,
                )

            yield {"type": "trace", "event": append_trace(
                trace, "generator", "生成 Agent",
                status="done",
                used_llm=bool(generator.settings.deepseek_api_key),
                latency_ms=timer.ms(),
                detail=f"生成完成 | 引用 {len(gen_output.citations)} 条",
                data={"citation_count": len(gen_output.citations)},
            )}

            yield {"type": "trace", "event": append_trace(
                trace, "reviewer", "评审 Agent", status="running",
                detail="核验免责声明与数值一致性…",
            )}
            timer = StepTimer()
            review = reviewer.run(query, gen_output.answer, chunks, calculations)
            review_used_llm = (
                reviewer.settings.reviewer_use_llm == "always"
                and bool(reviewer.settings.deepseek_api_key)
            )
            if review_used_llm:
                llm_calls += 1

            yield {"type": "trace", "event": append_trace(
                trace, "reviewer", "评审 Agent",
                status="done",
                used_llm=review_used_llm,
                latency_ms=timer.ms(),
                detail=(
                    f"verdict={review.verdict} | "
                    f"{'调用 LLM' if review_used_llm else '规则评审'} | "
                    f"{review.feedback or '无问题'}"
                ),
                data={"verdict": review.verdict, "feedback": review.feedback},
            )}

            if review.verdict == "pass" or review_retries >= max_retries:
                citations = gen_output.citations or format_citations(chunks)
                response = HealthResponse(
                    answer=gen_output.answer,
                    citations=citations,
                    retrieved_chunks=chunks,
                    calculations=calculations,
                    review_status=review.verdict,
                    review_feedback=review.feedback,
                    plan=plan.model_dump(),
                    metadata={
                        "llm_calls": llm_calls,
                        "trace": trace,
                        "profile": profile.to_context(),
                    },
                )
                self._last_response = response
                yield {"type": "done", "response": response}
                break

            review_feedback = review.feedback
            review_retries += 1
            yield {"type": "trace", "event": append_trace(
                trace, "reviewer", "评审失败重试",
                status="done",
                detail=f"打回 Generator 重写（第 {review_retries} 次）: {review_feedback}",
            )}
