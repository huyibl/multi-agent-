"""规划 Agent：意图识别与任务拆解。"""

import json
import re
from typing import Any, Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import PlannerOutput
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.llm_factory import invoke_llm_json


class PlannerAgent(BaseAgent):
    prompt_name = "planner"

    def run(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
    ) -> PlannerOutput:
        profile = profile or UserProfile()
        prompts = self.prompt
        user = prompts["user_template"].format(
            query=query,
            profile=json.dumps(profile.to_context(), ensure_ascii=False),
        )
        if self.settings.deepseek_api_key:
            data = invoke_llm_json(
                self.llm,
                prompts["system"],
                user,
                fallback=self._rule_based_plan(query, profile),
            )
        else:
            data = self._rule_based_plan(query, profile)

        return PlannerOutput(
            intent=data.get("intent", "general_health"),
            subtasks=data.get("subtasks", ["retrieve_guideline", "calc_metrics", "generate_advice"]),
            entities=data.get("entities", {}),
            retrieval_queries=data.get(
                "retrieval_queries",
                self._default_retrieval_queries(query),
            ),
        )

    def _rule_based_plan(self, query: str, profile: UserProfile) -> dict[str, Any]:
        """LLM 不可用时的规则兜底规划。"""
        entities = self._extract_entities(query)
        merged = profile.merge_from_entities(entities)
        intent = "general_health"
        q_lower = query.lower()
        if any(k in query for k in ("增肌", "muscle", "bulk", "蛋白")):
            intent = "muscle_gain_nutrition"
        elif any(k in query for k in ("减肥", "减重", "lose")):
            intent = "weight_loss"
        return {
            "intent": intent,
            "subtasks": ["retrieve_guideline", "calc_metrics", "generate_advice"],
            "entities": {**merged.to_context(), **entities},
            "retrieval_queries": self._default_retrieval_queries(query),
        }

    def _extract_entities(self, query: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        height = re.search(r"身高\s*(\d{2,3})|(\d{2,3})\s*cm", query, re.I)
        if height:
            entities["height_cm"] = float(height.group(1) or height.group(2))
        weight = re.search(r"体重\s*(\d{2,3})|(\d{2,3})\s*kg", query, re.I)
        if weight:
            entities["weight_kg"] = float(weight.group(1) or weight.group(2))
        if "增肌" in query:
            entities["goal"] = "muscle_gain"
        if "减肥" in query or "减重" in query:
            entities["goal"] = "lose_weight"
        return entities

    def _default_retrieval_queries(self, query: str) -> list[str]:
        queries = [query]
        if "蛋白" in query:
            queries.append("增肌 蛋白质 摄入量 推荐 g/kg")
        if "热量" in query or "卡路里" in query:
            queries.append("每日总热量 膳食指南 推荐")
        return queries
