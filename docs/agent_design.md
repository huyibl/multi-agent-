# Agent 设计

## Agent 职责一览

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| Planner | 意图识别、任务拆解 | query, profile | PlannerOutput |
| Retriever | RAG 检索权威片段 | query, plan | list[RetrievedChunk] |
| Calculator | 确定性营养计算 | profile, plan | CalculationResults |
| Generator | 个性化建议生成 | plan, chunks, calculations | GeneratorOutput |
| Reviewer | 一致性与免责声明核验 | answer, chunks, calculations | ReviewerOutput |

## Prompt 设计原则

- Prompt 模板位于 `config/prompts/*.yaml`
- 要求 LLM **输出 JSON**，便于解析与测试
- Calculator **不依赖 LLM 算数**，仅使用 Python tools

## Planner Agent

- 提取实体：身高、体重、目标（增肌/减重）
- 生成 `retrieval_queries` 供 RAG 使用
- **兜底**：正则提取 + 规则 intent（无 API Key 时可用）

## Retriever Agent

- 根据 intent 过滤 `doc_type`：dietary_guideline, exercise, nutrition_table
- 多 query 检索并去重

## Calculator Agent

- 调用 `tools/bmi.py`, `tools/tdee.py`, `tools/macros.py`
- 增肌目标蛋白质：1.6～2.2 g/kg（ISSN 范围）

## Generator Agent

- 数值必须与 `calculation_results` 一致
- 引用格式 `[1][2]`
- 必须包含免责声明
- **兜底**：模板化答案（无 API Key 时）

## Reviewer Agent

- 规则检查：免责声明、蛋白质数值范围
- LLM 检查：与检索来源矛盾（需 API Key）
- `verdict=fail` 时触发 LangGraph 循环

## 状态管理

```python
class HealthState(TypedDict):
    query: str
    profile: UserProfile
    plan: PlannerOutput
    retrieved_chunks: list[RetrievedChunk]
    calculation_results: CalculationResults
    generator_output: GeneratorOutput
    review_result: ReviewerOutput
    review_retries: int
```

## 面试常见问题

**Q: 为什么 Calculator 不用 LLM？**  
A: 营养数值需要可复现、可单测；LLM 可能算错，Reviewer 对照工具结果核验。

**Q: 评审循环如何避免无限循环？**  
A: `MAX_REVIEW_RETRIES=2`，超过则强制结束。

**Q: 无 API Key 如何 Demo？**  
A: Planner/Generator/Reviewer 均有 rule-based fallback；Embedding 默认 local bge-m3。
