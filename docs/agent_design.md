# Agent 设计

## 职责一览

| Agent | 职责 | 关键输入 | 输出 |
|-------|------|----------|------|
| Planner | 意图、实体、检索词；支持历史追问 | query, profile, history | `PlannerOutput` |
| Retriever | Chroma 语义检索 + doc_type 过滤 | query, plan | `list[RetrievedChunk]` |
| Calculator | BMI / 蛋白 / TDEE / 宏量（纯工具） | profile, plan | `CalculationResults` |
| Generator | 健身建议 Markdown / JSON + 引用 | query, plan, chunks, calc, history | `GeneratorOutput` |
| Reviewer | 免责声明与蛋白数值一致性 | answer, chunks, calc | `ReviewerOutput` |

Prompt：`config/prompts/*.yaml`。在线流式使用 Generator 的 `stream_system`（直接 Markdown）。

## Planner

- 规则抽取：身高/体重/年龄/性别/目标关键词。
- `PLANNER_USE_LLM=auto`：意图明确走规则；短句追问走 LLM 消解指代。
- 无历史实体时从近期用户消息回填。

## Retriever

- Intent → doc_type（膳食 / 运动 / 营养表）。
- `RETRIEVAL_MERGE_QUERIES=true` 时合并为单次相似度检索。

## Calculator

- 不调用 LLM 做算术；增肌蛋白常用 1.6～2.2 g/kg。
- 缺少身高体重时部分字段为空，由对话引导用户补充。

## Generator

- 数值须与 `calculation_results` 一致；结尾强制免责声明。
- 流式路径：`stream_tokens` → UI；非流式：`invoke_llm_json`。
- 无 API Key：模板答案兜底。

## Reviewer

- `auto`：规则通过即 pass（免责声明；蛋白相关句中的建议克数范围）。
- `always`：额外 LLM 深度评审。
- `fail` 时带 feedback 打回 Generator，最多 `MAX_REVIEW_RETRIES`。

## 编排与状态

在线：`ChatService.ask_events` 产出 `trace` / `token` / `profile` / `done`。  
图定义：`graph/workflow.py` — analyzer 式并行在节点 `parallel_fetch`（retriever∥calculator）。

共享状态见 `graph/state.py` 的 `HealthState`（query、profile、plan、chunks、calculations、generator/reviewer 输出、retries）。

## 面试要点

**为何计算不用 LLM？** 可复现、可单测；Reviewer 对照工具输出。  
**如何避免评审死循环？** `MAX_REVIEW_RETRIES`。  
**无 Key 能否 Demo？** 规则/模板兜底；Embedding 可用 DashScope。
