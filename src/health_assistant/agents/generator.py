"""生成 Agent：合成个性化健康建议。"""

import json
from typing import Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import (
    CalculationResults,
    GeneratorOutput,
    PlannerOutput,
    RetrievedChunk,
)
from health_assistant.utils.citation_formatter import format_chunks_for_prompt
from health_assistant.utils.llm_factory import invoke_llm_json


class GeneratorAgent(BaseAgent):
    prompt_name = "generator"

    def run(
        self,
        query: str,
        plan: PlannerOutput,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
        review_feedback: str = "",
    ) -> GeneratorOutput:
        prompts = self.prompt
        calc_data = calculations.model_dump() if calculations else {}
        user = prompts["user_template"].format(
            query=query,
            plan=json.dumps(plan.model_dump(), ensure_ascii=False),
            chunks=format_chunks_for_prompt(chunks),
            calculations=json.dumps(calc_data, ensure_ascii=False),
            review_feedback=review_feedback or "无",
        )

        if self.settings.deepseek_api_key:
            data = invoke_llm_json(
                self.llm,
                prompts["system"],
                user,
                fallback=self._template_answer(query, chunks, calculations),
            )
            return GeneratorOutput(
                answer=data.get("answer", ""),
                citations=data.get("citations", []),
            )

        fallback = self._template_answer(query, chunks, calculations)
        return GeneratorOutput(
            answer=fallback.get("answer", ""),
            citations=fallback.get("citations", []),
        )

    def _template_answer(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
    ) -> dict:
        """无 LLM 时的模板化兜底回答。"""
        parts = []
        if calculations.bmi:
            parts.append(f"您的 BMI 为 {calculations.bmi}（{calculations.bmi_category}）。")
        if calculations.protein_range_g:
            low, high = calculations.protein_range_g
            parts.append(f"建议每日蛋白质摄入 {low}～{high} 克。")
            if calculations.protein_per_kg:
                pl, ph = calculations.protein_per_kg
                parts.append(f"约 {pl}～{ph} g/kg 体重，符合增肌人群常见推荐范围。")
        if calculations.tdee_kcal:
            parts.append(f"估算每日总热量需求约 {calculations.tdee_kcal} 千卡。")

        if chunks:
            parts.append("参考来源：")
            for i, c in enumerate(chunks[:3], 1):
                parts.append(f"[{i}] {c.source}: {c.content[:80]}...")

        parts.append("\n以上内容仅供参考，不构成医疗建议。如有特殊健康状况请咨询专业医生或营养师。")
        citations = [f"{c.source}" for c in chunks[:5]]
        return {"answer": "\n".join(parts), "citations": citations}
