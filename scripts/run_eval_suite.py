#!/usr/bin/env python3
"""成本可控评测：50 条检索全量 + RAGAS-lite 抽样。"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from health_assistant.rag.ragas_lite import render_markdown_report, run_cost_controlled_eval


def main() -> None:
    """运行成本可控评测并写出 JSON / Markdown 报告。"""
    parser = argparse.ArgumentParser(description="Cost-controlled RAG evaluation suite")
    parser.add_argument(
        "--llm-sample",
        type=int,
        default=8,
        help="LLM 生成+评判抽样条数（默认 8；设 0 则仅检索）",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="跳过全部 LLM（只跑 50 条检索，成本最低）",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(ROOT / "docs" / "benchmarks"),
        help="报告输出目录",
    )
    args = parser.parse_args()

    print("=== Cost-controlled eval ===")
    print(f"dataset: 50 queries | llm_sample={0 if args.skip_llm else args.llm_sample}")
    print("Running...")

    payload = run_cost_controlled_eval(
        llm_sample=0 if args.skip_llm else args.llm_sample,
        top_k=args.top_k,
        skip_llm=args.skip_llm,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "eval_v1_cost_controlled.json"
    md_path = out_dir / "eval_v1_cost_controlled_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(payload))

    r = payload["retrieval"]["summary"]
    print("\n--- Retrieval (full 50) ---")
    for k, v in r.get("recall_at_k", {}).items():
        print(f"  {k}: {v:.1%}")
    print(f"  MRR: {r.get('mrr')}")
    print(f"  avg latency: {r.get('avg_latency_ms')} ms")

    lite = payload["ragas_lite"]
    print("\n--- RAGAS-lite ---")
    if lite.get("enabled"):
        m = lite["metrics"]
        print(f"  sample: {lite['sample_size']}")
        print(f"  faithfulness: {m['faithfulness']:.4f}")
        print(f"  answer_relevancy: {m['answer_relevancy']:.4f}")
        print(f"  context_precision: {m['context_precision']:.4f}")
    else:
        print(f"  skipped: {lite.get('skip_reason', 'n/a')}")

    cost = payload["cost_control"]
    print("\n--- Cost control ---")
    print(f"  embedding_calls≈{cost['embedding_calls_approx']}")
    print(f"  llm_calls≈{cost['llm_calls_approx']}")
    print(f"\nJSON: {json_path}")
    print(f"Report: {md_path}")


if __name__ == "__main__":
    main()
