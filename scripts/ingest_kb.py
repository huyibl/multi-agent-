#!/usr/bin/env python3
"""从原始文档构建向量知识库。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rich.console import Console

from health_assistant.services.ingest_service import IngestService

console = Console()


def main():
    console.print("[bold green]正在入库健康知识库...[/]")
    service = IngestService()
    result = service.run()
    console.print(f"已加载: {result['loaded']} 页")
    console.print(f"切块数: {result['chunks']}")
    console.print(f"已存储: {result['stored']}")


if __name__ == "__main__":
    main()
