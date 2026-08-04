#!/usr/bin/env python3
"""健康管理助手 CLI 调试入口。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rich.console import Console
from rich.markdown import Markdown

from health_assistant.schemas.user_profile import UserProfile
from health_assistant.services.chat_service import ChatService

console = Console()


def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "我身高172，体重70，想增肌，每天吃多少蛋白质？"
    )
    console.print(f"[bold]问题:[/] {query}\n")

    service = ChatService()
    profile = UserProfile(height_cm=172, weight_kg=70, age=28, sex="male")
    response = service.ask(query, profile=profile)

    console.print(Markdown(response.answer))
    console.print("\n[bold]计算结果:[/]")
    if response.calculations and response.calculations.protein_range_g:
        low, high = response.calculations.protein_range_g
        console.print(f"  蛋白质: {low}-{high} g")
    if response.calculations and response.calculations.bmi:
        console.print(f"  BMI: {response.calculations.bmi}")
    console.print(f"\n[bold]评审:[/] {response.review_status}")
    if response.citations:
        console.print("\n[bold]引用来源:[/]")
        for c in response.citations[:5]:
            console.print(f"  - {c}")


if __name__ == "__main__":
    main()
