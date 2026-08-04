#!/usr/bin/env python3
"""健康管理助手统一入口。"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="个人健康管理助手")
    parser.add_argument(
        "command",
        choices=["streamlit", "cli", "ingest", "eval"],
        help="要执行的命令",
    )
    parser.add_argument("query", nargs="*", help="CLI 模式下的查询内容")
    args = parser.parse_args()

    if args.command == "streamlit":
        app = ROOT / "app" / "streamlit_app.py"
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=False)
    elif args.command == "cli":
        cmd = [sys.executable, str(ROOT / "scripts" / "run_cli.py")] + args.query
        subprocess.run(cmd, check=False)
    elif args.command == "ingest":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "ingest_kb.py")], check=False)
    elif args.command == "eval":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "evaluate_rag.py")], check=False)


if __name__ == "__main__":
    main()
