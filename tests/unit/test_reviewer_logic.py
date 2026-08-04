"""评审 Agent 规则校验单元测试。"""

from health_assistant.agents.reviewer import ReviewerAgent
from health_assistant.schemas.agent_io import CalculationResults


def test_reviewer_missing_disclaimer():
    agent = ReviewerAgent()
    calc = CalculationResults(protein_range_g=(112, 154))
    issues = agent._rule_based_checks("建议每日蛋白质 120 克。", calc)
    assert any("免责声明" in i for i in issues)


def test_reviewer_passes_with_disclaimer():
    agent = ReviewerAgent()
    calc = CalculationResults(protein_range_g=(112, 154))
    answer = "建议每日蛋白质 112-154 克。以上内容仅供参考，不构成医疗建议。"
    issues = agent._rule_based_checks(answer, calc)
    assert not any("免责声明" in i for i in issues)
