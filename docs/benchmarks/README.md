# 评测与基准报告

基于当前代码与实测结果的索引。核心数字见根目录 [README](../../README.md)。

## 成本可控评测（推荐）

| 阶段 | 范围 | 成本 |
|------|------|------|
| 检索 | **50 条全量** Recall@K / MRR | 仅 Embedding |
| RAGAS-lite | 默认 **8 条抽样** Faithfulness / Relevancy / Context Precision | 每条约 2 次短 LLM 调用 |

```bash
python main.py eval-suite
# 或
python scripts/run_eval_suite.py --llm-sample 8

# 最低成本（无 LLM）
python scripts/run_eval_suite.py --skip-llm
```

输出：
- `eval_v1_cost_controlled.json`
- `eval_v1_cost_controlled_report.md`

## 优化前后 E2E 对比

```bash
python main.py benchmark
```

含 E2E 延迟、LLM 次数、评审 pass 率（见 `mvp_vs_optimized_v1_report.md`）。

## 数据集

[tests/fixtures/eval_queries.json](../../tests/fixtures/eval_queries.json) — 50 条，覆盖增肌/减脂/热量/宏量/补水/食物/个性化等场景。
