"""规划 Agent：意图识别与任务拆解。"""

import json
import re
from typing import Any, Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import PlannerOutput
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.chat_history import format_chat_history
from health_assistant.utils.llm_factory import invoke_llm_json

_CLEAR_INTENT_KEYWORDS = (
    "增肌", "减脂", "减肥", "减重", "蛋白", "热量", "卡路里", "kcal",
    "BMI", "bmi", "训练", "饮食", "膳食", "营养", "补水", "碳水", "脂肪",
    "muscle", "bulk", "lose", "calorie", "protein", "腹肌", "有氧", "力量",
)


class PlannerAgent(BaseAgent):
    """规划 Agent：意图识别、实体抽取与检索 Query 生成。

    明确意图时可走规则短路，避免不必要的 LLM 调用。
    """

    prompt_name = "planner"

    def run(
        self,
        query: str,
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> PlannerOutput:
        """根据当前问句、会话档案与历史生成 ``PlannerOutput``。"""
        profile = profile or UserProfile()
        history = history or []
        rule_plan = self._rule_based_plan(query, profile, history)

        use_llm = self._should_use_llm(query, rule_plan, history)
        if use_llm:
            prompts = self.prompt
            user = prompts["user_template"].format(
                query=query,
                profile=json.dumps(profile.to_context(), ensure_ascii=False),
                history=format_chat_history(history),
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
            intent=data.get("intent", "general_fitness"),
            subtasks=data.get(
                "subtasks",
                ["retrieve_guideline", "calc_metrics", "generate_advice"],
            ),
            entities=data.get("entities", {}),
            retrieval_queries=data.get(
                "retrieval_queries",
                self._default_retrieval_queries(query),
            ),
        )

    def _should_use_llm(
        self,
        query: str,
        rule_plan: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> bool:
        """按 ``PLANNER_USE_LLM`` 与问句清晰度决定是否调用 LLM。"""
        mode = self.settings.planner_use_llm
        if mode == "never":
            return False
        if mode == "always":
            return bool(self.settings.deepseek_api_key)
        if not self.settings.deepseek_api_key:
            return False
        # 有历史且当前句很短/像追问 → 走 LLM 理解指代
        if history and self._looks_like_followup(query):
            return True
        return not self._is_clear_intent(query, rule_plan)

    def _looks_like_followup(self, query: str) -> bool:
        """启发式判断是否为短追问（指代需 LLM 理解）。"""
        q = query.strip()
        if len(q) <= 12:
            return True
        follow_markers = ("那", "还", "继续", "刚才", "上面", "呢", "吗", "怎么", "多少")
        return any(m in q for m in follow_markers) and not any(
            k in q for k in ("身高", "体重", "cm", "kg")
        )

    def _is_clear_intent(self, query: str, rule_plan: dict[str, Any]) -> bool:
        """问句是否含明确健身/营养关键词，可跳过 Planner LLM。"""
        q = query.lower()
        if any(kw.lower() in q or kw in query for kw in _CLEAR_INTENT_KEYWORDS):
            return True
        return rule_plan.get("intent") not in ("general_fitness", "general_health", "", None)

    def _rule_based_plan(
        self,
        query: str,
        profile: UserProfile,
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """无 LLM 时的规则规划：抽实体、推断意图、生成检索词。"""
        entities = self._extract_entities(query)
        # 追问时从历史用户消息补抽实体
        if not entities.get("height_cm") or not entities.get("weight_kg"):
            for msg in reversed(history):
                if msg.get("role") != "user":
                    continue
                hist_ent = self._extract_entities(msg.get("content") or "")
                for k, v in hist_ent.items():
                    entities.setdefault(k, v)

        merged = profile.merge_from_entities(entities)
        intent = "general_fitness"
        text = query + " " + " ".join(
            m.get("content", "") for m in history[-4:] if m.get("role") == "user"
        )
        if any(k in text for k in ("增肌", "muscle", "bulk", "蛋白", "腹肌")):
            intent = "muscle_gain_nutrition"
        elif any(k in text for k in ("减肥", "减重", "lose", "减脂")):
            intent = "weight_loss"
        elif any(k in query for k in ("热量", "卡路里", "kcal", "TDEE")):
            intent = "calorie_nutrition"
        elif any(k in query for k in ("训练", "有氧", "力量", "动作")):
            intent = "training_advice"

        return {
            "intent": intent,
            "subtasks": ["retrieve_guideline", "calc_metrics", "generate_advice"],
            "entities": {**merged.to_context(), **entities},
            "retrieval_queries": self._default_retrieval_queries(query),
        }

    def _extract_entities(self, query: str) -> dict[str, Any]:
        """用正则从自然语言中抽取身高/体重/年龄/性别/目标。"""
        entities: dict[str, Any] = {}
        height = re.search(r"身高\s*(\d{2,3})|(\d{2,3})\s*cm", query, re.I)
        if height:
            entities["height_cm"] = float(height.group(1) or height.group(2))
        weight = re.search(r"体重\s*(\d{2,3}(?:\.\d+)?)|(\d{2,3}(?:\.\d+)?)\s*kg", query, re.I)
        if weight:
            entities["weight_kg"] = float(weight.group(1) or weight.group(2))
        age = re.search(r"年龄\s*(\d{1,3})|(\d{1,3})\s*岁", query)
        if age:
            entities["age"] = int(age.group(1) or age.group(2))
        if "男" in query and "女" not in query:
            entities["sex"] = "male"
        if "女" in query:
            entities["sex"] = "female"
        if "增肌" in query or "腹肌" in query:
            entities["goal"] = "muscle_gain"
        if "减肥" in query or "减重" in query or "减脂" in query:
            entities["goal"] = "lose_weight"
        return entities

    def _default_retrieval_queries(self, query: str) -> list[str]:
        """默认检索 Query：直接使用用户原问句。"""
        return [query]
