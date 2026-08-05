#!/usr/bin/env python3

"""生成性能测试报告（RAG + 端到端延迟），支持 MVP 与 optimized_v1 对比。"""



import argparse

import json

import subprocess

import sys

import time

from datetime import datetime, timezone

from pathlib import Path



ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "src"))



from config.settings import get_settings

from health_assistant.rag.eval import run_rag_evaluation

from health_assistant.rag.loaders import iter_source_files

from health_assistant.schemas.user_profile import UserProfile

from health_assistant.services.chat_service import ChatService



BENCHMARK_DIR = ROOT / "docs" / "benchmarks"

E2E_QUERIES = [

    "我身高172，体重70，想增肌，每天吃多少蛋白质？",

    "减脂期间蛋白质应该怎么吃？",

    "每日热量大概需要多少？",

]



VERSION_CONFIG = {

    "mvp-baseline": {

        "json_name": "mvp_baseline.json",

        "md_name": "mvp_baseline_report.md",

        "title": "MVP 基线性能测试报告",

        "intro": "本报告用于记录 **优化前 MVP** 的 RAG 与端到端性能基线，便于与后续优化版本对比。",

    },

    "optimized_v1": {

        "json_name": "optimized_v1.json",

        "md_name": "optimized_v1_report.md",

        "title": "optimized_v1 性能测试报告",

        "intro": "本报告记录 **规则短路 + 并行检索/计算 + 流式体验** 优化后的 RAG 与端到端性能。",

    },

}





def count_kb_files() -> int:

    settings = get_settings()

    return sum(1 for _ in iter_source_files(settings.data_raw_dir))





def run_pytest() -> dict:

    start = time.perf_counter()

    proc = subprocess.run(

        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],

        cwd=ROOT,

        capture_output=True,

        text=True,

    )

    elapsed = time.perf_counter() - start

    passed = failed = 0

    import re



    match_pass = re.search(r"(\d+) passed", proc.stdout)

    match_fail = re.search(r"(\d+) failed", proc.stdout)

    if match_pass:

        passed = int(match_pass.group(1))

    if match_fail:

        failed = int(match_fail.group(1))

    return {

        "exit_code": proc.returncode,

        "passed": passed,

        "failed": failed,

        "duration_sec": round(elapsed, 2),

        "success": proc.returncode == 0,

    }





def run_e2e_benchmark() -> list[dict]:

    service = ChatService()

    profile = UserProfile(height_cm=172, weight_kg=70, age=28, sex="male")

    results = []

    for query in E2E_QUERIES:

        start = time.perf_counter()

        response = service.ask(query, profile=profile)

        elapsed_ms = (time.perf_counter() - start) * 1000

        chunk_count = len(response.retrieved_chunks)

        protein = None

        if response.calculations and response.calculations.protein_range_g:

            protein = list(response.calculations.protein_range_g)

        results.append(

            {

                "query": query,

                "latency_ms": round(elapsed_ms, 2),

                "review_status": response.review_status,

                "retrieved_chunks": chunk_count,

                "protein_range_g": protein,

                "has_citations": bool(response.citations or response.retrieved_chunks),

                "llm_calls": response.metadata.get("llm_calls", 0),

            }

        )

    return results





def _e2e_summary(e2e: list[dict]) -> dict:

    latencies = [x["latency_ms"] for x in e2e]

    llm_calls = [x.get("llm_calls", 0) for x in e2e]

    pass_count = sum(1 for x in e2e if x["review_status"] == "pass")

    return {

        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,

        "max_latency_ms": round(max(latencies), 2) if latencies else 0,

        "avg_llm_calls": round(sum(llm_calls) / len(llm_calls), 2) if llm_calls else 0,

        "review_pass_rate": round(pass_count / len(e2e), 4) if e2e else 0,

    }





def build_comparison_section(mvp: dict, opt: dict) -> list[str]:

    mvp_e2e = _e2e_summary(mvp["e2e"])

    opt_e2e = _e2e_summary(opt["e2e"])

    mvp_rag = mvp["rag"]["summary"]

    opt_rag = opt["rag"]["summary"]



    def delta(new_val, old_val, lower_is_better=True):

        if old_val == 0:

            return "-"

        pct = (new_val - old_val) / old_val * 100

        improved = pct < 0 if lower_is_better else pct > 0

        sign = "+" if pct > 0 else ""

        arrow = "↓" if improved else "↑"

        return f"{sign}{pct:.1f}% {arrow}"



    lines = [

        "# MVP vs optimized_v1 对比报告",

        "",

        f"> 生成时间（UTC）：{datetime.now(timezone.utc).isoformat()}",

        "",

        "## 核心指标对比",

        "",

        "| 指标 | MVP | optimized_v1 | 变化 |",

        "|------|-----|--------------|------|",

        f"| E2E 平均延迟 (ms) | {mvp_e2e['avg_latency_ms']} | {opt_e2e['avg_latency_ms']} | {delta(opt_e2e['avg_latency_ms'], mvp_e2e['avg_latency_ms'])} |",

        f"| E2E 最大延迟 (ms) | {mvp_e2e['max_latency_ms']} | {opt_e2e['max_latency_ms']} | {delta(opt_e2e['max_latency_ms'], mvp_e2e['max_latency_ms'])} |",

        f"| LLM 调用/问 (avg) | {mvp_e2e['avg_llm_calls']} | {opt_e2e['avg_llm_calls']} | {delta(opt_e2e['avg_llm_calls'], mvp_e2e['avg_llm_calls'])} |",

        f"| 评审 pass 率 | {mvp_e2e['review_pass_rate']:.0%} | {opt_e2e['review_pass_rate']:.0%} | {delta(opt_e2e['review_pass_rate'], mvp_e2e['review_pass_rate'], lower_is_better=False)} |",

        f"| Recall@5 | {mvp_rag['recall_at_k']['recall@5']:.1%} | {opt_rag['recall_at_k']['recall@5']:.1%} | {delta(opt_rag['recall_at_k']['recall@5'], mvp_rag['recall_at_k']['recall@5'], lower_is_better=False)} |",

        f"| MRR | {mvp_rag['mrr']:.4f} | {opt_rag['mrr']:.4f} | {delta(opt_rag['mrr'], mvp_rag['mrr'], lower_is_better=False)} |",

        f"| RAG 平均延迟 (ms) | {mvp_rag['avg_latency_ms']} | {opt_rag['avg_latency_ms']} | {delta(opt_rag['avg_latency_ms'], mvp_rag['avg_latency_ms'])} |",

        "",

        "## 优化措施摘要",

        "",

        "- Planner/Reviewer 规则优先（`PLANNER_USE_LLM=auto`、`REVIEWER_USE_LLM=auto`）",

        "- Retriever 单次 embedding 检索（`RETRIEVAL_MERGE_QUERIES=true`）",

        "- LangGraph Retriever ∥ Calculator 并行 fan-out",

        "- ChatService 单例 + Generator 流式输出",

        "",

    ]

    return lines





def build_markdown_report(data: dict, version: str) -> str:

    cfg = VERSION_CONFIG[version]

    rag = data["rag"]

    e2e = data["e2e"]

    pytest_info = data["pytest"]

    settings = data["environment"]

    e2e_sum = _e2e_summary(e2e)



    lines = [

        f"# {cfg['title']}",

        "",

        f"> 生成时间（UTC）：{data['generated_at']}",

        f"> 版本标签：`{data['version']}`",

        "",

        cfg["intro"],

        "",

        "## 1. 测试环境",

        "",

        "| 项 | 值 |",

        "|----|-----|",

        f"| Embedding 提供商 | {settings['embedding_provider']} |",

        f"| Embedding 模型 | {settings['embedding_model']} |",

        f"| LLM 模型 | {settings['deepseek_model']} |",

        f"| LLM API Key 已配置 | {settings['llm_configured']} |",

        f"| Planner LLM 模式 | {settings['planner_use_llm']} |",

        f"| Reviewer LLM 模式 | {settings['reviewer_use_llm']} |",

        f"| 检索 Query 合并 | {settings['retrieval_merge_queries']} |",

        f"| 知识库文件数 | {data['kb_file_count']} |",

        f"| Chunk Size / Overlap | {settings['chunk_size']} / {settings['chunk_overlap']} |",

        f"| Retrieval Top-K | {settings['retrieval_top_k']} |",

        "",

        "## 2. RAG 检索质量",

        "",

        "| 指标 | 值 |",

        "|------|-----|",

    ]

    for key, val in rag["summary"]["recall_at_k"].items():

        lines.append(f"| {key} | {val:.1%} |")

    lines.extend(

        [

            f"| MRR | {rag['summary']['mrr']:.4f} |",

            f"| Hit Rate (任一 K 命中) | {rag['summary']['hit_rate_any']:.1%} |",

            f"| 平均检索延迟 (ms) | {rag['summary']['avg_latency_ms']} |",

            f"| 评估 Query 数 | {rag['summary']['total_queries']} |",

            "",

            "### 逐条 Query 结果",

            "",

            "| ID | Query | Recall@1 | Recall@3 | Recall@5 | MRR | 延迟(ms) |",

            "|----|-------|----------|----------|----------|-----|----------|",

        ]

    )

    for d in rag["details"]:

        h = d["hit_at_k"]

        r1 = "Y" if h.get(1) or h.get("1") else "N"

        r3 = "Y" if h.get(3) or h.get("3") else "N"

        r5 = "Y" if h.get(5) or h.get("5") else "N"

        q_short = d["query"][:28] + "..." if len(d["query"]) > 28 else d["query"]

        lines.append(

            f"| {d['query_id']} | {q_short} | {r1} | {r3} | {r5} | {d['reciprocal_rank']:.2f} | {d['latency_ms']} |"

        )



    lines.extend(

        [

            "",

            "## 3. 端到端多 Agent 延迟",

            "",

            "| Query | 延迟(ms) | LLM 次数 | 评审 | 检索块数 | 蛋白质范围(g) |",

            "|-------|----------|----------|------|----------|---------------|",

        ]

    )

    for item in e2e:

        protein = item["protein_range_g"] or "-"

        q_short = item["query"][:24] + "..." if len(item["query"]) > 24 else item["query"]

        lines.append(

            f"| {q_short} | {item['latency_ms']} | {item.get('llm_calls', '-')} | {item['review_status']} | {item['retrieved_chunks']} | {protein} |"

        )



    lines.extend(

        [

            "",

            f"- **E2E 平均延迟**：{e2e_sum['avg_latency_ms']} ms",

            f"- **E2E 最大延迟**：{e2e_sum['max_latency_ms']} ms",

            f"- **LLM 调用/问（平均）**：{e2e_sum['avg_llm_calls']}",

            f"- **评审 pass 率**：{e2e_sum['review_pass_rate']:.0%}",

            "",

            "## 4. 单元/集成测试",

            "",

            f"- 通过：{pytest_info['passed']}，失败：{pytest_info['failed']}",

            f"- 耗时：{pytest_info['duration_sec']} s",

            f"- 状态：{'PASS' if pytest_info['success'] else 'FAIL'}",

            "",

            "## 5. 复现命令",

            "",

            "```bash",

            "python main.py ingest",

            f"python scripts/run_benchmark.py --version {version}",

            "```",

            "",

        ]

    )

    return "\n".join(lines)





def main():

    parser = argparse.ArgumentParser(description="Health Assistant benchmark")

    parser.add_argument(

        "--version",

        choices=list(VERSION_CONFIG.keys()),

        default="optimized_v1",

        help="Benchmark version tag (default: optimized_v1)",

    )

    args = parser.parse_args()

    version = args.version

    cfg = VERSION_CONFIG[version]



    settings = get_settings()

    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)



    print(f"Running benchmark for version: {version}")

    print("Running RAG evaluation...")

    rag_summary = run_rag_evaluation(k_values=[1, 3, 5], top_k=settings.retrieval_top_k)



    print("Running E2E benchmark...")

    e2e_results = run_e2e_benchmark()



    print("Running pytest...")

    pytest_results = run_pytest()



    generated_at = datetime.now(timezone.utc).isoformat()

    payload = {

        "generated_at": generated_at,

        "version": version,

        "kb_file_count": count_kb_files(),

        "environment": {

            "embedding_provider": settings.embedding_provider,

            "embedding_model": settings.embedding_model,

            "deepseek_model": settings.deepseek_model,

            "llm_configured": bool(settings.deepseek_api_key),

            "planner_use_llm": settings.planner_use_llm,

            "reviewer_use_llm": settings.reviewer_use_llm,

            "retrieval_merge_queries": settings.retrieval_merge_queries,

            "chunk_size": settings.chunk_size,

            "chunk_overlap": settings.chunk_overlap,

            "retrieval_top_k": settings.retrieval_top_k,

        },

        "rag": {

            "summary": {k: v for k, v in rag_summary.items() if k != "details"},

            "details": rag_summary["details"],

        },

        "e2e": e2e_results,

        "e2e_summary": _e2e_summary(e2e_results),

        "pytest": pytest_results,

    }



    json_path = BENCHMARK_DIR / cfg["json_name"]

    md_path = BENCHMARK_DIR / cfg["md_name"]



    with open(json_path, "w", encoding="utf-8") as f:

        json.dump(payload, f, ensure_ascii=False, indent=2)



    md_content = build_markdown_report(payload, version)

    with open(md_path, "w", encoding="utf-8") as f:

        f.write(md_content)



    # 若跑 optimized_v1 且存在 MVP 基线，生成对比报告

    mvp_json = BENCHMARK_DIR / "mvp_baseline.json"

    if version == "optimized_v1" and mvp_json.exists():

        with open(mvp_json, encoding="utf-8") as f:

            mvp_data = json.load(f)

        compare_path = BENCHMARK_DIR / "mvp_vs_optimized_v1_report.md"

        compare_lines = build_comparison_section(mvp_data, payload)

        with open(compare_path, "w", encoding="utf-8") as f:

            f.write("\n".join(compare_lines))

        print(f"Comparison Report: {compare_path}")



    print(f"\nBenchmark JSON: {json_path}")

    print(f"Benchmark Report: {md_path}")

    print(f"Recall@5: {rag_summary['recall_at_k']['recall@5']:.1%}")

    print(f"MRR: {rag_summary['mrr']:.4f}")

    e2e_sum = _e2e_summary(e2e_results)

    print(f"E2E avg latency: {e2e_sum['avg_latency_ms']} ms")

    print(f"LLM calls/query (avg): {e2e_sum['avg_llm_calls']}")





if __name__ == "__main__":

    main()

