"""构建并编译 LangGraph 工作流。"""

from langgraph.graph import END, StateGraph

from health_assistant.graph.edges import route_after_review
from health_assistant.graph.nodes import (
    calculator_node,
    generator_node,
    planner_node,
    retriever_node,
    reviewer_node,
)
from health_assistant.graph.state import HealthState


def build_workflow(checkpointer=None):
    """构建多 Agent 健康管理图工作流。"""
    graph = StateGraph(HealthState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("calculator", calculator_node)
    graph.add_node("generator", generator_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "calculator")
    graph.add_edge("calculator", "generator")
    graph.add_edge("generator", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"generator": "generator", "end": END},
    )

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


def build_workflow_with_sqlite(db_path: str = ":memory:"):
    """使用 SQLite 检查点构建工作流，支持会话持久化。"""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        from langgraph_checkpoint_sqlite import SqliteSaver  # type: ignore

    checkpointer = SqliteSaver.from_conn_string(db_path)
    return build_workflow(checkpointer=checkpointer)
