"""计算 Agent：确定性营养数值计算。"""

import json
from typing import Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import CalculationResults, PlannerOutput
from health_assistant.schemas.user_profile import HealthGoal, UserProfile
from health_assistant.tools import bmi_category, calculate_bmi, calculate_macros, calculate_protein_range, calculate_tdee


class CalculatorAgent(BaseAgent):
    prompt_name = "calculator"

    def run(
        self,
        profile: UserProfile,
        plan: PlannerOutput,
    ) -> CalculationResults:
        merged = profile.merge_from_entities(plan.entities)
        result = CalculationResults()

        if merged.height_cm and merged.weight_kg:
            result.bmi = calculate_bmi(merged.height_cm, merged.weight_kg)
            result.bmi_category = bmi_category(result.bmi)

        if merged.weight_kg:
            goal = merged.goal
            if plan.intent == "muscle_gain_nutrition":
                goal = HealthGoal.MUSCLE_GAIN
            protein_range = calculate_protein_range(merged.weight_kg, goal)
            result.protein_range_g = protein_range
            low, high = protein_range
            result.protein_per_kg = (round(low / merged.weight_kg, 2), round(high / merged.weight_kg, 2))

        if all([merged.weight_kg, merged.height_cm, merged.age, merged.sex]):
            result.tdee_kcal = calculate_tdee(
                merged.weight_kg,
                merged.height_cm,
                merged.age,
                merged.sex,
                merged.activity_level,
            )
            macros = calculate_macros(result.tdee_kcal, merged.weight_kg, merged.goal)
            result.carbs_g = macros["carbs_g"]
            result.fat_g = macros["fat_g"]
            result.raw = macros

        # API 可用时可选调用 LLM 做结果摘要
        if self.settings.deepseek_api_key and result.raw:
            prompts = self.prompt
            user = prompts["user_template"].format(
                profile=json.dumps(merged.to_context(), ensure_ascii=False),
                intent=plan.intent,
                entities=json.dumps(plan.entities, ensure_ascii=False),
            )
            # 计算 Agent 主要依赖工具；LLM 调用仅为可选增强
            _ = user

        return result
