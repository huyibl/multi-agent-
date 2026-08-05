# 性能基准测试说明

本目录存放各版本的 RAG 与端到端性能报告，用于 **优化前后对比**。

## 文件说明

| 文件 | 说明 |
|------|------|
| `mvp_baseline_report.md` | MVP 版本可读报告 |
| `mvp_baseline.json` | MVP 版本机器可读原始数据 |
| `rag_eval_latest.json` | 最近一次 RAG 评估结果 |

## 复现 MVP 基线

```bash
python main.py ingest
python main.py benchmark
```

## 核心对比指标

| 类别 | 指标 |
|------|------|
| RAG | Recall@1 / @3 / @5、MRR、平均检索延迟 |
| E2E | 多 Agent 全链路平均/最大延迟 |
| 质量 | pytest 通过数、评审 pass/fail |

## 优化后如何对比

1. 完成优化（如重排序、并行节点、ChatService 单例等）
2. 再次运行 `python main.py benchmark`
3. 将输出保存为 `docs/benchmarks/optimized_v1_report.md`（手动复制或改脚本版本标签）
4. 对比 `mvp_baseline_report.md` 与新版报告

## 评估数据集

- 路径：[tests/fixtures/eval_queries.json](../tests/fixtures/eval_queries.json)
- 15 条标注 query，按 `expected_sources` / `expected_doc_type` 判定命中
