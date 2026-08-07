"""RAG 检索质量评估指标。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from health_assistant.rag.retriever_chain import HealthRetriever
from health_assistant.schemas.agent_io import RetrievedChunk


@dataclass
class QueryEvalResult:
    """单条 query 的评估结果。"""

    query_id: str
    query: str
    expected_sources: list[str]
    expected_doc_types: list[str]
    retrieved_sources: list[str]
    retrieved_doc_types: list[str]
    hit_at_k: dict[int, bool] = field(default_factory=dict)
    reciprocal_rank: float = 0.0
    latency_ms: float = 0.0
    top_k: int = 5

    @property
    def matched(self) -> bool:
        """任一 K 值命中即为 True。"""
        return any(self.hit_at_k.values()) if self.hit_at_k else False

    def to_dict(self) -> dict[str, Any]:
        """序列化为可写入 JSON 报告的字典。"""
        return {
            "query_id": self.query_id,
            "query": self.query,
            "expected_sources": self.expected_sources,
            "expected_doc_types": self.expected_doc_types,
            "retrieved_sources": self.retrieved_sources,
            "retrieved_doc_types": self.retrieved_doc_types,
            "hit_at_k": self.hit_at_k,
            "reciprocal_rank": round(self.reciprocal_rank, 4),
            "latency_ms": round(self.latency_ms, 2),
            "matched": self.matched,
        }


def _source_matches(retrieved_source: str, expected: str) -> bool:
    """判断检索来源是否命中期望（按文件名匹配）。"""
    return expected.lower() in retrieved_source.lower()


def _chunk_matches(chunk: RetrievedChunk, expected_sources: list[str], expected_doc_types: list[str]) -> bool:
    """判断 chunk 是否命中期望 source 或 doc_type。"""
    source_hit = any(_source_matches(chunk.source, exp) for exp in expected_sources)
    type_hit = chunk.doc_type in expected_doc_types if expected_doc_types else False
    if expected_sources and expected_doc_types:
        return source_hit or type_hit
    if expected_sources:
        return source_hit
    return type_hit


def evaluate_single_query(
    retriever: HealthRetriever,
    query_id: str,
    query: str,
    expected_sources: list[str],
    expected_doc_types: list[str],
    k_values: list[int] | None = None,
    top_k: int = 5,
) -> QueryEvalResult:
    """评估单条 query 的 Recall@K 与 RR。"""
    import time

    k_values = k_values or [1, 3, 5]
    max_k = max(max(k_values), top_k)

    start = time.perf_counter()
    chunks = retriever.retrieve([query], top_k=max_k)
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_sources = [c.source for c in chunks]
    retrieved_doc_types = [c.doc_type for c in chunks]

    hit_at_k: dict[int, bool] = {}
    for k in k_values:
        top_chunks = chunks[:k]
        hit_at_k[k] = any(
            _chunk_matches(c, expected_sources, expected_doc_types) for c in top_chunks
        )

    reciprocal_rank = 0.0
    for rank, chunk in enumerate(chunks, start=1):
        if _chunk_matches(chunk, expected_sources, expected_doc_types):
            reciprocal_rank = 1.0 / rank
            break

    return QueryEvalResult(
        query_id=query_id,
        query=query,
        expected_sources=expected_sources,
        expected_doc_types=expected_doc_types,
        retrieved_sources=retrieved_sources,
        retrieved_doc_types=retrieved_doc_types,
        hit_at_k=hit_at_k,
        reciprocal_rank=reciprocal_rank,
        latency_ms=latency_ms,
        top_k=top_k,
    )


def load_eval_queries(fixtures_path: Path | None = None) -> list[dict[str, Any]]:
    """加载评估 query 数据集。"""
    if fixtures_path is None:
        fixtures_path = (
            Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "eval_queries.json"
        )
    with open(fixtures_path, encoding="utf-8") as f:
        return json.load(f)


def run_rag_evaluation(
    retriever: HealthRetriever | None = None,
    fixtures_path: Path | None = None,
    k_values: list[int] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """运行完整 RAG 评估并返回汇总结果。"""
    retriever = retriever or HealthRetriever()
    k_values = k_values or [1, 3, 5]
    queries = load_eval_queries(fixtures_path)

    results: list[QueryEvalResult] = []
    for item in queries:
        result = evaluate_single_query(
            retriever=retriever,
            query_id=item.get("id", ""),
            query=item["query"],
            expected_sources=item.get("expected_sources", []),
            expected_doc_types=item.get("expected_doc_types", []),
            k_values=k_values,
            top_k=top_k,
        )
        results.append(result)

    n = len(results)
    summary: dict[str, Any] = {
        "total_queries": n,
        "k_values": k_values,
        "recall_at_k": {},
        "mrr": 0.0,
        "avg_latency_ms": 0.0,
        "hit_rate_any": 0.0,
    }

    for k in k_values:
        hits = sum(1 for r in results if r.hit_at_k.get(k, False))
        summary["recall_at_k"][f"recall@{k}"] = round(hits / n, 4) if n else 0.0

    summary["mrr"] = round(sum(r.reciprocal_rank for r in results) / n, 4) if n else 0.0
    summary["avg_latency_ms"] = round(sum(r.latency_ms for r in results) / n, 2) if n else 0.0
    summary["hit_rate_any"] = round(sum(1 for r in results if r.matched) / n, 4) if n else 0.0
    summary["details"] = [r.to_dict() for r in results]

    return summary
