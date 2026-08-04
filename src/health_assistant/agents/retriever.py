"""检索 Agent：从知识库进行 RAG 检索。"""

from typing import Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.rag.retriever_chain import HealthRetriever
from health_assistant.schemas.agent_io import PlannerOutput, RetrievedChunk


class RetrieverAgent(BaseAgent):
    prompt_name = "retriever"

    def __init__(self, retriever: Optional[HealthRetriever] = None, **kwargs):
        super().__init__(**kwargs)
        self.retriever = retriever or HealthRetriever(settings=self.settings)

    def run(
        self,
        query: str,
        plan: PlannerOutput,
    ) -> list[RetrievedChunk]:
        queries = plan.retrieval_queries or [query]
        doc_types = self._infer_doc_types(plan.intent)
        return self.retriever.retrieve(queries=queries, doc_types=doc_types)

    def _infer_doc_types(self, intent: str) -> list[str] | None:
        mapping = {
            "muscle_gain_nutrition": ["dietary_guideline", "exercise", "nutrition_table"],
            "weight_loss": ["dietary_guideline", "nutrition_table"],
            "general_health": None,
        }
        return mapping.get(intent)
