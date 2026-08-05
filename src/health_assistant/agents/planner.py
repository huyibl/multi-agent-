"""规划 Agent：意图识别与任务拆解。"""

import json
import re
from typing import Any, Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import PlannerOutput
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.llm_factory import invoke_llm_json

# 规则规划可识别的明确意图关键词
_CLEAR_INTENT_KEYWORDS = (
    "增肌", "减脂", "减肥", "减重", "蛋白", "热量", "卡路里", "kcal",
    "BMI", "bmi", "训练", "饮食", "膳食", "营养", "补水", "碳水", "脂肪",
    "muscle", "bulk", "lose", "calorie", "protein",
)


class PlannerAgent(BaseAgent):
    prompt_name = "planner"

    def run(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
    ) -> PlannerOutput:
        profile = profile or UserProfile()
        rule_plan = self._rule_based_plan(query, profile)

        use_llm = self._should_use_llm(query, rule_plan)
        if use_llm:
            prompts = self.prompt
            user = prompts["user_template"].format(
                query=query,
                profile=json.dumps(profile.to_context(), ensure_ascii=False),
            )
            data = invoke_llm_json(
                self.llm,
                prompts["system"],
                user,
                fallback=rule_plan,
            )
        else:
            data = rule_plan

        return PlannerOutput(
            intent=data.get("intent", "general_health"),
            subtasks=data.get("subtasks", ["retrieve_guideline", "calc_metrics", "generate_advice"]),
            entities=data.get("entities", {}),
            retrieval_queries=data.get(
                "retrieval_queries",
                self._default_retrieval_queries(query),
            ),
        )

    def _should_use_llm(self, query: str, rule_plan: dict[str, Any]) -> bool:
        mode = self.settings.planner_use_llm
        if mode == "never":
            return False
        if mode == "always":
            return bool(self.settings.deepseek_api_key)
        # auto：意图明确则跳过 LLM
        if not self.settings.deepseek_api_key:
            return False
        return not self._is_clear_intent(query, rule_plan)

    def _is_clear_intent(self, query: str, rule_plan: dict[str, Any]) -> bool:
        q = query.lower()
        if any(kw.lower() in q or kw in query for kw in _CLEAR_INTENT_KEYWORDS):
            return True
        return rule_plan.get("intent") not in ("general_health", "", None)

    def _rule_based_plan(self, query: str, profile: UserProfile) -> dict[str, Any]:
        """规则兜底规划。"""
        entities = self._extract_entities(query)
        merged = profile.merge_from_entities(entities)
        intent = "general_health"
        if any(k in query for k in ("增肌", "muscle", "bulk", "蛋白")):
            intent = "muscle_gain_nutrition"
        elif any(k in query for k in ("减肥", "减重", "lose", "减脂")):
            intent = "weight_loss"
        elif any(k in query for k in ("热量", "卡路里", "kcal", "TDEE")):
            intent = "calorie_nutrition"
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
        return [query]
