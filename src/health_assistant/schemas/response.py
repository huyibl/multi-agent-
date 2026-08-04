"""最终 API 响应数据模型。"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from health_assistant.schemas.agent_io import CalculationResults, RetrievedChunk


class HealthResponse(BaseModel):
    """返回给前端的结构化响应。"""

    answer: str
    citations: list[str] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    calculations: Optional[CalculationResults] = None
    review_status: str = "pass"
    review_feedback: str = ""
    plan: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
