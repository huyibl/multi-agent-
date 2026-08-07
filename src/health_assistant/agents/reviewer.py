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
    """评审 Agent：核验免责声明与蛋白质等数值一致性。

    默认规则通过即 pass；仅 ``REVIEWER_USE_LLM=always`` 时再调 LLM。
    """

    prompt_name = "reviewer"

    def run(
        self,
        query: str,
        answer: str,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
    ) -> ReviewerOutput:
        """对生成答案做规则（及可选 LLM）评审。"""
        issues = self._rule_based_checks(answer, calculations, query)
        if issues:
            return ReviewerOutput(verdict="fail", feedback="; ".join(issues), issues=issues)

        # auto/never：规则通过即 pass，不调 LLM
        if self.settings.reviewer_use_llm != "always" or not self.settings.deepseek_api_key:
            return ReviewerOutput(verdict="pass", feedback="")

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

    def _extract_recommended_protein_g(self, answer: str) -> list[float]:
        """提取蛋白质相关语句中的建议克数，忽略碳水/脂肪等其它营养素数值。"""
        numbers: list[float] = []
        protein_segments = [
            seg
            for seg in re.split(r"[。\n]", answer)
            if "蛋白" in seg or "protein" in seg.lower()
        ]
        text = "。".join(protein_segments)
        if not text:
            return numbers

        range_patterns = (
            r"(\d+(?:\.\d+)?)\s*[～~\-至]\s*(\d+(?:\.\d+)?)\s*克",
            r"(\d+(?:\.\d+)?)\s*[～~\-至]\s*(\d+(?:\.\d+)?)\s*g(?:/天)?",
        )
        for pattern in range_patterns:
            for match in re.finditer(pattern, text, re.I):
                numbers.extend([float(match.group(1)), float(match.group(2))])
        for match in re.finditer(
            r"(?:建议|推荐|每天|每日|摄入|需要|约)[^。\n]{0,40}?(\d+(?:\.\d+)?)\s*(?:克|g(?:/天)?)",
            text,
            re.I,
        ):
            numbers.append(float(match.group(1)))
        return numbers

    def _rule_based_checks(
        self,
        answer: str,
        calculations: Optional[CalculationResults],
        query: str = "",
    ) -> list[str]:
        """规则门禁：免责声明缺失或蛋白质数值严重偏离则 fail。"""
        issues = []
        if "医疗建议" not in answer and "仅供参考" not in answer:
            issues.append("缺少免责声明")

        calorie_only = any(k in query for k in ("热量", "卡路里", "kcal", "TDEE")) and "蛋白" not in query
        if calorie_only:
            return issues

        if calculations and calculations.protein_range_g:
            if "蛋白" not in answer and "protein" not in answer.lower():
                return issues
            low, high = calculations.protein_range_g
            numbers = self._extract_recommended_protein_g(answer)
            daily_floor = max(50.0, low * 0.4)
            for num in numbers:
                if num < daily_floor:
                    continue
                if not validate_protein_in_range(num, (low, high), tolerance=0.2):
                    if num < low * 0.5 or num > high * 1.5:
                        issues.append(
                            f"答案中蛋白质数值 {num}g 与计算范围 {low}-{high}g 不一致"
                        )
                        break
        return issues
