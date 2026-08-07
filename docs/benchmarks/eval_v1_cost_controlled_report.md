# 成本可控评测报告（50 条 + RAGAS-lite）

> 版本：`eval_v1_cost_controlled` | 评测集：50 条

## 成本管控策略

- 检索全量：**50** 条（约 50 次 Embedding，无生成 LLM）
- LLM 抽样：**8** 条（约 16 次短调用：生成+评判）
- 说明：生成+评判使用短上下文与低温度；检索全量不加 LLM。DeepSeek Flash 下通常仅分货币级成本。

## 1. 检索质量（全量）

| 指标 | 值 |
|------|-----|
| recall@1 | 98.0% |
| recall@3 | 100.0% |
| recall@5 | 100.0% |
| MRR | 0.9900 |
| Hit Rate | 100.0% |
| 平均检索延迟 | 489.2 ms |
| 耗时 | 24.46 s |

## 2. RAGAS-lite（抽样 LLM 评判）

- 抽样条数：8
- 耗时：31.7 s

| 指标 | 分数 (0-1) |
|------|------------|
| Faithfulness | 0.9625 |
| Answer Relevancy | 1.0000 |
| Context Precision | 1.0000 |

### 抽样明细

| ID | Scenario | Faith | Relevancy | CtxPrec |
|----|----------|-------|-----------|---------|
| q02 | calorie | 1.00 | 1.00 | 1.00 |
| q06 | fat_loss | 1.00 | 1.00 | 1.00 |
| q04 | food | 1.00 | 1.00 | 1.00 |
| q05 | guideline | 0.80 | 1.00 | 1.00 |
| q09 | hydration | 1.00 | 1.00 | 1.00 |
| q08 | macros | 1.00 | 1.00 | 1.00 |
| q01 | muscle_gain | 0.90 | 1.00 | 1.00 |
| q15 | personal | 1.00 | 1.00 | 1.00 |

## 3. 与优化收益的关系

本报告量化 **检索质量** 与 **生成可信度（抽样）**；
端到端延迟 / LLM 次数对比仍见 `docs/benchmarks/mvp_vs_optimized_v1_report.md`。

复现：

```bash
python scripts/run_eval_suite.py --llm-sample 8
```
