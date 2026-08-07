"""生成 Agent：合成个性化健身建议。"""

import json
from collections.abc import Iterator
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from health_assistant.agents.base import BaseAgent
from health_assistant.schemas.agent_io import (
    CalculationResults,
    GeneratorOutput,
    PlannerOutput,
    RetrievedChunk,
)
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.utils.chat_history import format_chat_history
from health_assistant.utils.citation_formatter import format_chunks_for_prompt
from health_assistant.utils.llm_factory import extract_json, invoke_llm_json

DISCLAIMER = (
    "\n\n以上内容仅供参考，不构成医疗建议。如有特殊健康状况，请咨询专业医生或注册营养师。"
)


def _normalize_citations(raw: list) -> list[str]:
    """将 LLM 返回的引用（str / dict）统一为字符串列表。"""
    result: list[str] = []
    for item in raw or []:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            summary = item.get("summary") or item.get("source") or str(item)
            idx = item.get("index")
            result.append(f"[{idx}] {summary}" if idx is not None else str(summary))
        else:
            result.append(str(item))
    return result


def _ensure_disclaimer(answer: str) -> str:
    """若答案缺少免责声明则追加标准尾注。"""
    if "仅供参考" in answer or "医疗建议" in answer:
        return answer
    return answer.rstrip() + DISCLAIMER


def _strip_code_fence(text: str) -> str:
    """去掉 Markdown 代码围栏，便于流式原文当答案用。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class GeneratorAgent(BaseAgent):
    """生成 Agent：综合检索、计算与历史对话输出个性化建议。"""

    prompt_name = "generator"

    def _build_messages(
        self,
        query: str,
        plan: PlannerOutput,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
        review_feedback: str,
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
        stream: bool = False,
    ):
        """组装 Generator 的 system/user 消息；流式可用精简 system。"""
        prompts = self.prompt
        calc_data = calculations.model_dump() if calculations else {}
        profile = profile or UserProfile()
        history = history or []
        user = prompts["user_template"].format(
            query=query,
            profile=json.dumps(profile.to_context(), ensure_ascii=False),
            history=format_chat_history(history),
            plan=json.dumps(plan.model_dump(), ensure_ascii=False),
            chunks=format_chunks_for_prompt(chunks),
            calculations=json.dumps(calc_data, ensure_ascii=False),
            review_feedback=review_feedback or "无",
        )
        system = prompts.get("stream_system", prompts["system"]) if stream else prompts["system"]
        return [SystemMessage(content=system), HumanMessage(content=user)]

    def run(
        self,
        query: str,
        plan: PlannerOutput,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
        review_feedback: str = "",
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> GeneratorOutput:
        """非流式生成完整答案与引用；无 API Key 时用模板兜底。"""
        if self.settings.deepseek_api_key:
            messages = self._build_messages(
                query, plan, chunks, calculations, review_feedback,
                profile=profile, history=history,
            )
            data = invoke_llm_json(
                self.llm,
                messages[0].content,
                messages[1].content,
                fallback=self._template_answer(query, chunks, calculations),
            )
            answer = _ensure_disclaimer(data.get("answer", ""))
            return GeneratorOutput(
                answer=answer,
                citations=_normalize_citations(data.get("citations", [])),
            )

        fallback = self._template_answer(query, chunks, calculations)
        return GeneratorOutput(
            answer=fallback.get("answer", ""),
            citations=fallback.get("citations", []),
        )

    def stream_tokens(
        self,
        query: str,
        plan: PlannerOutput,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
        review_feedback: str = "",
        profile: Optional[UserProfile] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """流式产出 Token；无 API Key 时一次 yield 模板答案。"""
        if not self.settings.deepseek_api_key:
            yield self._template_answer(query, chunks, calculations).get("answer", "")
            return

        messages = self._build_messages(
            query, plan, chunks, calculations, review_feedback,
            profile=profile, history=history, stream=True,
        )
        for chunk in self.llm.stream(messages):
            text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            if text:
                yield text

    def output_from_stream(self, raw: str, chunks: list[RetrievedChunk]) -> GeneratorOutput:
        """将流式拼接原文解析为 ``GeneratorOutput``（优先 JSON）。"""
        data = extract_json(raw)
        if data and data.get("answer"):
            answer = _ensure_disclaimer(data.get("answer", ""))
            citations = _normalize_citations(data.get("citations", []))
        else:
            answer = _ensure_disclaimer(_strip_code_fence(raw))
            citations = [c.source for c in chunks[:5]]
        return GeneratorOutput(answer=answer, citations=citations)

    def _template_answer(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        calculations: Optional[CalculationResults],
    ) -> dict:
        """无 LLM 时的模板答案：拼接计算结果与检索摘要。"""
        parts = []
        if calculations and calculations.bmi:
            parts.append(f"您的 BMI 为 {calculations.bmi}（{calculations.bmi_category}）。")
        if calculations and calculations.protein_range_g:
            low, high = calculations.protein_range_g
            parts.append(f"建议每日蛋白质摄入 {low}～{high} 克。")
            if calculations.protein_per_kg:
                pl, ph = calculations.protein_per_kg
                parts.append(f"约 {pl}～{ph} g/kg 体重，符合增肌人群常见推荐范围。")
        if calculations and calculations.tdee_kcal:
            parts.append(f"估算每日总热量需求约 {calculations.tdee_kcal} 千卡。")

        if chunks:
            parts.append("参考来源：")
            for i, c in enumerate(chunks[:3], 1):
                parts.append(f"[{i}] {c.source}: {c.content[:80]}...")

        parts.append(DISCLAIMER.strip())
        citations = [f"{c.source}" for c in chunks[:5]]
        return {"answer": "\n".join(parts), "citations": citations}
