# MVP vs optimized_v1 对比报告

> 生成时间（UTC）：2026-08-05T08:53:07.512104+00:00

## 核心指标对比

| 指标 | MVP | optimized_v1 | 变化 |
|------|-----|--------------|------|
| E2E 平均延迟 (ms) | 46477.07 | 8872.37 | -80.9% ↓ |
| E2E 最大延迟 (ms) | 50374.77 | 10980.69 | -78.2% ↓ |
| LLM 调用/问 (avg) | 0.0 | 1.0 | - |
| 评审 pass 率 | 67% | 100% | +50.0% ↓ |
| Recall@5 | 100.0% | 100.0% | 0.0% ↑ |
| MRR | 0.9667 | 1.0000 | +3.4% ↓ |
| RAG 平均延迟 (ms) | 522.61 | 1045.03 | +100.0% ↑ |

## 优化措施摘要

- Planner/Reviewer 规则优先（`PLANNER_USE_LLM=auto`、`REVIEWER_USE_LLM=auto`）
- Retriever 单次 embedding 检索（`RETRIEVAL_MERGE_QUERIES=true`）
- LangGraph Retriever ∥ Calculator 并行 fan-out
- ChatService 单例 + Generator 流式输出
