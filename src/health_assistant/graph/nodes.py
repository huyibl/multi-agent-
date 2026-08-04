"""LangGraph 节点函数，封装各 Agent。"""

from health_assistant.agents.calculator import CalculatorAgent
from health_assistant.agents.generator import GeneratorAgent
from health_assistant.agents.planner import PlannerAgent
from health_assistant.agents.retriever import RetrieverAgent
from health_assistant.agents.reviewer import ReviewerAgent
from health_assistant.graph.state import HealthState
from health_assistant.schemas.user_profile import UserProfile


def planner_node(state: HealthState) -> dict:
    agent = PlannerAgent()
    profile = state.get("profile") or UserProfile()
    plan = agent.run(query=state["query"], profile=profile)
    merged_profile = profile.merge_from_entities(plan.entities)
    return {"plan": plan, "profile": merged_profile}


def retriever_node(state: HealthState) -> dict:
    agent = RetrieverAgent()
    chunks = agent.run(query=state["query"], plan=state["plan"])
    return {"retrieved_chunks": chunks}


def calculator_node(state: HealthState) -> dict:
    agent = CalculatorAgent()
    profile = state.get("profile") or UserProfile()
    results = agent.run(profile=profile, plan=state["plan"])
    return {"calculation_results": results}


def generator_node(state: HealthState) -> dict:
    agent = GeneratorAgent()
    output = agent.run(
        query=state["query"],
        plan=state["plan"],
        chunks=state.get("retrieved_chunks", []),
        calculations=state.get("calculation_results"),
        review_feedback=state.get("review_feedback", ""),
    )
    return {"generator_output": output}


def reviewer_node(state: HealthState) -> dict:
    agent = ReviewerAgent()
    gen = state.get("generator_output")
    answer = gen.answer if gen else ""
    result = agent.run(
        query=state["query"],
        answer=answer,
        chunks=state.get("retrieved_chunks", []),
        calculations=state.get("calculation_results"),
    )
    retries = state.get("review_retries", 0)
    update: dict = {"review_result": result}
    if result.verdict == "fail":
        update["review_feedback"] = result.feedback
        update["review_retries"] = retries + 1
    return update
