#!/usr/bin/env python3
"""简易 RAG 召回率评估脚本。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from health_assistant.rag.retriever_chain import HealthRetriever

TEST_QUERIES = [
    "增肌 蛋白质 摄入量",
    "每日热量 推荐",
    "抗阻力训练 营养",
    "鸡胸肉 蛋白质含量",
    "膳食指南 蛋白质",
]


def main():
    retriever = HealthRetriever()
    hits = 0
    for q in TEST_QUERIES:
        chunks = retriever.retrieve([q], top_k=3)
        if chunks:
            hits += 1
            print(f"✓ {q}: {len(chunks)} 块, 首条来源={chunks[0].source}")
        else:
            print(f"✗ {q}: 无结果")
    print(f"\nRecall@3: {hits}/{len(TEST_QUERIES)} = {hits/len(TEST_QUERIES):.0%}")


if __name__ == "__main__":
    main()
