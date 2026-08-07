# 面试答辩要点（AI 健身教练）

## 30 秒介绍

这是一个 **RAG + 多 Agent** 的健身营养助手：用户对话说明身体数据与目标后，系统先规划任务，再并行检索知识库与工具计算 BMI/蛋白质，最后生成带引用的建议并由评审门禁校验。做过规则短路与并行优化，E2E 从约 **46s 降到 9s**，常见问句 LLM 从 3 次降到 1 次；有 **50 条**检索评测与抽样 RAGAS-lite。

## 必讲三点

1. **Tool 与 LLM 分离**：算数走 Python，LLM 只解读；避免「一本正经算错」。
2. **可观测协作**：侧边栏 Agent Trace（规则/LLM、耗时、来源）。
3. **可量化优化**：MVP vs optimized_v1 + `eval-suite` 报告。

## 架构口述

`Planner → (Retriever ∥ Calculator) → Generator → Reviewer`；UI 用 `ask_events` 流式输出；多轮历史与会话档案跨轮保留。

## 数据口径（用实测）

| 指标 | 数值 |
|------|------|
| E2E | 46.5s → **8.9s** |
| LLM/问 | 3 → **1** |
| Recall@5 / MRR（50 条） | **100% / 0.99** |
| Faithfulness（抽样 8） | **0.96** |

## 常见追问

- **为何不用完整 RAGAS 全量生成？** 控 Token：检索 50 全量，LLM 评判分层抽样 8 条。  
- **档案 Tab 哪去了？** 产品改为对话优先，实体从聊天累积到 sidebar。  
- **知识库用户能改吗？** 不能；`?admin=1` 才是管理员入库。

## 文档

[architecture.md](architecture.md) · [benchmarks/](benchmarks/) · 根目录 [README.md](../README.md)
