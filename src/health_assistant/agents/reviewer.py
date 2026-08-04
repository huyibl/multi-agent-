"""评审 Agent：核验建议与来源、计算结果的一致性。"""

import json
import re

from typing import Optional

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import CalculationResults, RetrievedChunk, ReviewerOutput
from health_assistant.tools.validators import validate_protein_in_range
from health_assistant.utils.citation_formatter import format_chunks_for_prompt
from health_assistant.utils.llm_factory import invoke_llm_json


class ReviewerAgent(BaseAgent):
    prompt_name = "reviewer"

    def run(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
    ) -> ReviewerOutput:
        issues = self._rule_based_checks(answer, calculations)
        if issues:
            return ReviewerOutput(verdict="fail", feedback="; ".join(issues), issues=issues)

        if self.settings.deepseek_api_key:
            prompts = self.prompt
            user = prompts["user_template"].format(
                query=query,
                answer=answer,
                chunks=format_chunks_for_prompt(chunks),
                calculations=json.dumps(
                    calculations.model_dump() if calculations else {}, ensure_ascii=False
                ),
            )
            data = invoke_llm_json(
                self.llm,
                prompts["system"],
                user,
                fallback={"verdict": "pass", "feedback": ""},
            )
            return ReviewerOutput(
                verdict=data.get("verdict", "pass"),
                feedback=data.get("feedback", ""),
                issues=data.get("issues", []),
            )

        return ReviewerOutput(verdict="pass", feedback="")

    def _rule_based_checks(
        self,
        answer: str,
        calculations: Optional[CalculationResults],
    ) -> list[str]:
        issues = []
        if "医疗建议" not in answer and "仅供参考" not in answer:
            issues.append("缺少免责声明")

        if calculations and calculations.protein_range_g:
            low, high = calculations.protein_range_g
            numbers = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)\s*克", answer)]
            for num in numbers:
                if num > 50 and not validate_protein_in_range(num, (low, high), tolerance=0.2):
                    if num < low * 0.5 or num > high * 1.5:
                        issues.append(f"答案中蛋白质数值 {num}g 与计算范围 {low}-{high}g 不一致")
                        break
        return issues
