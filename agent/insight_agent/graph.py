import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes import agent_step, answer, intent_classify, plan, reflect, route_after_agent, route_after_intent


class AgentState(TypedDict):
    question: str
    task_id: str
    session_id: str
    history: list
    user_id: str
    intent: str
    plan: list[str]
    current_step: int
    step_count: int
    max_steps: int | None
    cost_cap_cny: float | None
    sql: str | None
    query_result: list | None
    chart_spec: dict | None
    file: dict | None
    final_answer: str | None
    errors: list
    tool_calls: Annotated[list, operator.add]
    usage: Annotated[list, operator.add]
    reflect_note: str | None
    fix_hint: str | None


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent_classify", intent_classify)
    graph.add_node("plan", plan)
    graph.add_node("agent_step", agent_step)
    graph.add_node("reflect", reflect)
    graph.add_node("answer", answer)

    graph.set_entry_point("intent_classify")
    graph.add_conditional_edges(
        "intent_classify",
        route_after_intent,
        {"data_analysis": "plan", "knowledge_qa": "agent_step", "clarify": "answer"},
    )
    graph.add_edge("plan", "agent_step")
    graph.add_conditional_edges(
        "agent_step",
        route_after_agent,
        {"reflect": "reflect", "answer": "answer"},
    )
    graph.add_edge("reflect", "agent_step")
    graph.add_edge("answer", END)

    return graph.compile(checkpointer=MemorySaver())
