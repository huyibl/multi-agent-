#!/usr/bin/env python3
"""RAG 检索质量评估：Recall@K、MRR、延迟。"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rich.console import Console
from rich.table import Table

from health_assistant.rag.eval import run_rag_evaluation

console = Console()


def main():
    parser = argparse.ArgumentParser(description="RAG 检索质量评估")
    parser.add_argument("--top-k", type=int, default=5, help="检索 Top-K")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="JSON 报告输出路径，默认 docs/benchmarks/rag_eval_latest.json",
    )
    args = parser.parse_args()

    console.print("[bold green]Running RAG evaluation...[/]")
    summary = run_rag_evaluation(k_values=[1, 3, 5], top_k=args.top_k)

    table = Table(title="RAG Evaluation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total queries", str(summary["total_queries"]))
    for key, val in summary["recall_at_k"].items():
        table.add_row(key, f"{val:.1%}")
    table.add_row("MRR", f"{summary['mrr']:.4f}")
    table.add_row("Hit rate (any K)", f"{summary['hit_rate_any']:.1%}")
    table.add_row("Avg latency (ms)", str(summary["avg_latency_ms"]))
    console.print(table)

    console.print("\n[bold]Per-query results:[/]")
    for detail in summary["details"]:
        status = "✓" if detail["matched"] else "✗"
        hits = ", ".join(f"@{k}={'Y' if v else 'N'}" for k, v in detail["hit_at_k"].items())
        console.print(f"  {status} [{detail['query_id']}] {detail['query'][:40]}... ({hits})")

    output_path = Path(args.output) if args.output else ROOT / "docs" / "benchmarks" / "rag_eval_latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "mvp-baseline",
        "summary": {k: v for k, v in summary.items() if k != "details"},
        "details": summary["details"],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    console.print(f"\n[green]Report saved to {output_path}[/]")


if __name__ == "__main__":
    main()
