"""Agent 输入/输出数据模型。"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PlannerOutput(BaseModel):
    intent: str = "general_health"
    subtasks: list[str] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    retrieval_queries: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    content: str
    source: str = ""
    page: Optional[int] = None
    doc_type: str = ""
    score: float = 0.0


class CalculationResults(BaseModel):
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    tdee_kcal: Optional[float] = None
    protein_range_g: Optional[tuple[float, float]] = None
    protein_per_kg: Optional[tuple[float, float]] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class GeneratorOutput(BaseModel):
    answer: str = ""
    citations: list[str] = Field(default_factory=list)


class ReviewerOutput(BaseModel):
    verdict: Literal["pass", "fail"] = "pass"
    feedback: str = ""
    issues: list[str] = Field(default_factory=list)
