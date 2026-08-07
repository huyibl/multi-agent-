"""LangGraph 节点函数，封装各 Agent（实例复用）。"""

from concurrent.futures import ThreadPoolExecutor

from health_assistant.agents.calculator import CalculatorAgent
from health_assistant.agents.generator import GeneratorAgent
from health_assistant.agents.planner import PlannerAgent
from health_assistant.agents.retriever import RetrieverAgent
from health_assistant.agents.reviewer import ReviewerAgent
from health_assistant.graph.state import HealthState
from health_assistant.schemas.user_profile import UserProfile

_agent_pool: dict = {}


def _get_agent(name: str, cls):
    """按名称复用 Agent 实例，避免每节点重复初始化。"""
    if name not in _agent_pool:
        _agent_pool[name] = cls()
    return _agent_pool[name]


def planner_node(state: HealthState) -> dict:
    """规划节点：更新档案并写入 ``plan`` / LLM 计数。"""
    agent = _get_agent("planner", PlannerAgent)
    profile = state.get("profile") or UserProfile()
    rule_plan = agent._rule_based_plan(state["query"], profile)
    used_llm = agent._should_use_llm(state["query"], rule_plan)
    plan = agent.run(query=state["query"], profile=profile)
    merged_profile = profile.merge_from_entities(plan.entities)
    meta = dict(state.get("metadata") or {})
    if used_llm:
        meta["llm_calls"] = meta.get("llm_calls", 0) + 1
    return {"plan": plan, "profile": merged_profile, "metadata": meta}


def retriever_node(state: HealthState) -> dict:
    """检索节点：写入 ``retrieved_chunks``。"""
    agent = _get_agent("retriever", RetrieverAgent)
    chunks = agent.run(query=state["query"], plan=state["plan"])
    return {"retrieved_chunks": chunks}


def calculator_node(state: HealthState) -> dict:
    """计算节点：写入 ``calculation_results``。"""
    agent = _get_agent("calculator", CalculatorAgent)
    profile = state.get("profile") or UserProfile()
    results = agent.run(profile=profile, plan=state["plan"])
    return {"calculation_results": results}


def parallel_fetch_node(state: HealthState) -> dict:
    """并行执行检索与计算（Retriever ∥ Calculator）。"""
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_r = pool.submit(retriever_node, state)
        fut_c = pool.submit(calculator_node, state)
        r_result = fut_r.result()
        c_result = fut_c.result()
    return {**r_result, **c_result}


def generator_node(state: HealthState) -> dict:
    """生成节点：写入 ``generator_output``。"""
    agent = _get_agent("generator", GeneratorAgent)
    output = agent.run(
        query=state["query"],
        plan=state["plan"],
        chunks=state.get("retrieved_chunks", []),
        calculations=state.get("calculation_results"),
        review_feedback=state.get("review_feedback", ""),
    )
    meta = dict(state.get("metadata") or {})
    if agent.settings.deepseek_api_key:
        meta["llm_calls"] = meta.get("llm_calls", 0) + 1
    return {"generator_output": output, "metadata": meta}


def reviewer_node(state: HealthState) -> dict:
    """评审节点：写入评审结果；失败时递增 ``review_retries``。"""
    agent = _get_agent("reviewer", ReviewerAgent)
    gen = state.get("generator_output")
    answer = gen.answer if gen else ""
    result = agent.run(
        query=state["query"],
        answer=answer,
        chunks=state.get("retrieved_chunks", []),
        calculations=state.get("calculation_results"),
    )
    meta = dict(state.get("metadata") or {})
    if agent.settings.reviewer_use_llm == "always" and agent.settings.deepseek_api_key:
        meta["llm_calls"] = meta.get("llm_calls", 0) + 1
    retries = state.get("review_retries", 0)
    update: dict = {"review_result": result, "metadata": meta}
    if result.verdict == "fail":
        update["review_feedback"] = result.feedback
        update["review_retries"] = retries + 1
    return update
