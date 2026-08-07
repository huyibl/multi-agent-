"""
低成本 RAGAS 风格评估（Faithfulness / Answer Relevancy / Context Precision）。

成本策略：
- 检索指标：全量 N 条，仅 Embedding（无 LLM）
- 生成+评判：默认抽样 llm_sample 条，用 DeepSeek 短 JSON 评判（每条约 2 次小调用）
- 不强制安装完整 ragas 包，避免额外依赖与默认 OpenAI 高成本
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from health_assistant.rag.eval import load_eval_queries, run_rag_evaluation
from health_assistant.rag.retriever_chain import HealthRetriever
from health_assistant.utils.llm_factory import create_llm, extract_json


JUDGE_SYSTEM = """你是严格的 RAG 评估员。只输出 JSON，不要其它文字。
分数均为 0~1 的小数。
字段：
- faithfulness: 答案是否可由给定检索上下文支持（捏造则低分）
- answer_relevancy: 答案与用户问题的相关性
- context_precision: 检索上下文对回答该问题是否有用
- reason: 一句话理由
"""


def _truncate(text: str, n: int = 800) -> str:
    """截断长文本以控制评测 LLM 成本。"""
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + "…"


def _select_sample(queries: list[dict], sample_size: int, seed: int = 42) -> list[dict]:
    """按 scenario 分层轮转抽样，尽量覆盖核心场景。"""
    if sample_size <= 0 or sample_size >= len(queries):
        return list(queries)
    # 按 scenario 分层，尽量覆盖核心场景
    by_scene: dict[str, list[dict]] = {}
    for q in queries:
        by_scene.setdefault(q.get("scenario", "other"), []).append(q)
    selected: list[dict] = []
    scenes = sorted(by_scene.keys())
    i = 0
    while len(selected) < sample_size and any(by_scene.values()):
        scene = scenes[i % len(scenes)]
        if by_scene[scene]:
            # 稳定选取：按 id 排序后轮转
            by_scene[scene].sort(key=lambda x: x.get("id", ""))
            selected.append(by_scene[scene].pop(0))
        i += 1
        if i > sample_size * 20:
            break
    # 不够则按 id 补齐
    if len(selected) < sample_size:
        rest = [q for q in queries if q not in selected]
        rest.sort(key=lambda x: x.get("id", ""))
        selected.extend(rest[: sample_size - len(selected)])
    return selected[:sample_size]


def _generate_short_answer(llm, query: str, contexts: list[str]) -> str:
    """低成本短答：限制上下文与输出长度。"""
    ctx = "\n---\n".join(_truncate(c, 350) for c in contexts[:3])
    prompt = (
        f"根据下列资料用中文简要回答（不超过120字）。若资料不足请说明。\n"
        f"问题：{query}\n资料：\n{ctx}\n"
        f"最后一句加：以上内容仅供参考，不构成医疗建议。"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    return _truncate(text, 500)


def _judge_scores(llm, query: str, answer: str, contexts: list[str]) -> dict[str, Any]:
    """用 LLM 评判 Faithfulness / Relevancy / Context Precision。"""
    ctx = "\n---\n".join(_truncate(c, 300) for c in contexts[:3])
    user = (
        f"问题：{query}\n\n答案：{_truncate(answer, 400)}\n\n"
        f"检索上下文：\n{ctx}\n\n输出 JSON。"
    )
    resp = llm.invoke([SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=user)])
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    data = extract_json(text) or {}
    def _clip(x, default=0.0):
        try:
            v = float(x)
            return max(0.0, min(1.0, v))
        except Exception:
            return default
    return {
        "faithfulness": _clip(data.get("faithfulness"), 0.0),
        "answer_relevancy": _clip(data.get("answer_relevancy"), 0.0),
        "context_precision": _clip(data.get("context_precision"), 0.0),
        "reason": str(data.get("reason", ""))[:200],
    }


def estimate_cost_hint(retrieval_n: int, llm_sample: int) -> dict[str, Any]:
    """粗算调用量，便于成本管控说明（非精确账单）。"""
    # 检索：每 query 1 次 embedding
    # LLM 抽样：1 次短生成 + 1 次评判
    return {
        "retrieval_queries": retrieval_n,
        "embedding_calls_approx": retrieval_n,
        "llm_sample": llm_sample,
        "llm_calls_approx": llm_sample * 2,
        "note": "生成+评判使用短上下文与低温度；检索全量不加 LLM。DeepSeek Flash 下通常仅分货币级成本。",
    }


def run_cost_controlled_eval(
    *,
    llm_sample: int = 8,
    top_k: int = 5,
    fixtures_path: Optional[Any] = None,
    skip_llm: bool = False,
) -> dict[str, Any]:
    """
    运行成本可控评测：
    1) 全量检索 Recall@K / MRR
    2) 抽样 LLM：短生成 + RAGAS 风格三指标
    """
    queries = load_eval_queries(fixtures_path)
    retriever = HealthRetriever()

    t0 = time.perf_counter()
    retrieval = run_rag_evaluation(
        retriever=retriever,
        fixtures_path=fixtures_path,
        k_values=[1, 3, 5],
        top_k=top_k,
    )
    retrieval_sec = time.perf_counter() - t0

    llm_block: dict[str, Any] = {
        "enabled": False,
        "sample_size": 0,
        "metrics": {},
        "details": [],
    }

    if not skip_llm and llm_sample > 0:
        from config.settings import get_settings

        settings = get_settings()
        if not settings.deepseek_api_key:
            llm_block["skip_reason"] = "未配置 DEEPSEEK_API_KEY，跳过 LLM 评判"
        else:
            llm = create_llm(settings)
            # 降低输出长度控成本
            try:
                llm = llm.bind(max_tokens=256, temperature=0)
            except Exception:
                pass

            sample = _select_sample(queries, llm_sample)
            details = []
            scores = {"faithfulness": [], "answer_relevancy": [], "context_precision": []}

            t1 = time.perf_counter()
            for item in sample:
                chunks = retriever.retrieve([item["query"]], top_k=top_k)
                contexts = [c.content for c in chunks]
                answer = _generate_short_answer(llm, item["query"], contexts)
                judged = _judge_scores(llm, item["query"], answer, contexts)
                for k in scores:
                    scores[k].append(judged[k])
                details.append(
                    {
                        "query_id": item.get("id"),
                        "query": item["query"],
                        "scenario": item.get("scenario"),
                        "answer_preview": _truncate(answer, 160),
                        **judged,
                        "retrieved_sources": [c.source for c in chunks],
                    }
                )
            llm_sec = time.perf_counter() - t1

            def _avg(xs: list[float]) -> float:
                return round(sum(xs) / len(xs), 4) if xs else 0.0

            llm_block = {
                "enabled": True,
                "sample_size": len(sample),
                "duration_sec": round(llm_sec, 2),
                "metrics": {
                    "faithfulness": _avg(scores["faithfulness"]),
                    "answer_relevancy": _avg(scores["answer_relevancy"]),
                    "context_precision": _avg(scores["context_precision"]),
                },
                "details": details,
            }

    cost = estimate_cost_hint(len(queries), llm_block.get("sample_size", 0) if llm_block.get("enabled") else 0)

    return {
        "version": "eval_v1_cost_controlled",
        "dataset_size": len(queries),
        "cost_control": cost,
        "retrieval": {
            "duration_sec": round(retrieval_sec, 2),
            "summary": {k: v for k, v in retrieval.items() if k != "details"},
            "details": retrieval.get("details", []),
        },
        "ragas_lite": llm_block,
    }


def render_markdown_report(payload: dict[str, Any]) -> str:
    """将成本可控评测结果渲染为 Markdown 报告。"""
    r = payload["retrieval"]["summary"]
    lite = payload["ragas_lite"]
    cost = payload["cost_control"]
    lines = [
        "# 成本可控评测报告（50 条 + RAGAS-lite）",
        "",
        f"> 版本：`{payload['version']}` | 评测集：{payload['dataset_size']} 条",
        "",
        "## 成本管控策略",
        "",
        f"- 检索全量：**{cost['retrieval_queries']}** 条（约 {cost['embedding_calls_approx']} 次 Embedding，无生成 LLM）",
        f"- LLM 抽样：**{cost['llm_sample']}** 条（约 {cost['llm_calls_approx']} 次短调用：生成+评判）",
        f"- 说明：{cost['note']}",
        "",
        "## 1. 检索质量（全量）",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
    ]
    for k, v in r.get("recall_at_k", {}).items():
        lines.append(f"| {k} | {v:.1%} |")
    lines.extend(
        [
            f"| MRR | {r.get('mrr', 0):.4f} |",
            f"| Hit Rate | {r.get('hit_rate_any', 0):.1%} |",
            f"| 平均检索延迟 | {r.get('avg_latency_ms', 0)} ms |",
            f"| 耗时 | {payload['retrieval']['duration_sec']} s |",
            "",
            "## 2. RAGAS-lite（抽样 LLM 评判）",
            "",
        ]
    )
    if not lite.get("enabled"):
        lines.append(f"- 未启用：{lite.get('skip_reason', 'skip_llm 或 sample=0')}")
    else:
        m = lite["metrics"]
        lines.extend(
            [
                f"- 抽样条数：{lite['sample_size']}",
                f"- 耗时：{lite.get('duration_sec', '-')} s",
                "",
                "| 指标 | 分数 (0-1) |",
                "|------|------------|",
                f"| Faithfulness | {m.get('faithfulness', 0):.4f} |",
                f"| Answer Relevancy | {m.get('answer_relevancy', 0):.4f} |",
                f"| Context Precision | {m.get('context_precision', 0):.4f} |",
                "",
                "### 抽样明细",
                "",
                "| ID | Scenario | Faith | Relevancy | CtxPrec |",
                "|----|----------|-------|-----------|---------|",
            ]
        )
        for d in lite.get("details", []):
            lines.append(
                f"| {d.get('query_id')} | {d.get('scenario')} | "
                f"{d.get('faithfulness', 0):.2f} | {d.get('answer_relevancy', 0):.2f} | "
                f"{d.get('context_precision', 0):.2f} |"
            )

    lines.extend(
        [
            "",
            "## 3. 与优化收益的关系",
            "",
            "本报告量化 **检索质量** 与 **生成可信度（抽样）**；",
            "端到端延迟 / LLM 次数对比仍见 `docs/benchmarks/mvp_vs_optimized_v1_report.md`。",
            "",
            "复现：",
            "",
            "```bash",
            "python scripts/run_eval_suite.py --llm-sample 8",
            "```",
            "",
        ]
    )
    return "\n".join(lines)
