"""LangGraph 工作流的 HealthState 状态定义。"""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from health_assistant.schemas.agent_io import (
    CalculationResults,
    GeneratorOutput,
    PlannerOutput,
    RetrievedChunk,
    ReviewerOutput,
)
from health_assistant.schemas.user_profile import UserProfile


class HealthState(TypedDict, total=False):
    """在各 Agent 节点之间传递的共享状态。"""

    query: str
    profile: UserProfile
    plan: PlannerOutput
    retrieved_chunks: list[RetrievedChunk]
    calculation_results: CalculationResults
    generator_output: GeneratorOutput
    review_result: ReviewerOutput
    review_feedback: str
    review_retries: int
    messages: Annotated[list, add_messages]
    metadata: dict[str, Any]
