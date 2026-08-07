"""Agent 间传递的结构化输入/输出数据模型。"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PlannerOutput(BaseModel):
    """规划 Agent 输出：意图、子任务、实体与检索 Query。"""

    intent: str = "general_health"
    subtasks: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    retrieval_queries: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    """单条检索结果块及其元数据。"""

    content: str
    source: str = ""
    page: Optional[int] = None
    doc_type: str = ""
    score: float = 0.0


class CalculationResults(BaseModel):
    """计算 Agent 输出的 BMI / TDEE / 宏量等指标。"""

    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    tdee_kcal: Optional[float] = None
    protein_range_g: Optional[tuple[float, float]] = None
    protein_per_kg: Optional[tuple[float, float]] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class GeneratorOutput(BaseModel):
    """生成 Agent 输出：建议正文与引用来源。"""

    answer: str = ""
    citations: list[str] = Field(default_factory=list)


class ReviewerOutput(BaseModel):
    """评审 Agent 输出：通过/失败、反馈与问题列表。"""

    verdict: Literal["pass", "fail"] = "pass"
    feedback: str = ""
    issues: list[str] = Field(default_factory=list)
