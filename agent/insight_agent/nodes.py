import json
import re

from langchain_openai import ChatOpenAI

from .config import settings
from .prompts import ANSWER_SYSTEM, INTENT_SYSTEM, PLAN_SYSTEM, SQL_SYSTEM
from .tools import run_tool


def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0,
        timeout=settings.llm_timeout_seconds,
    )


def _extract_sql(text: str) -> str | None:
    match = re.search(r"```sql\n(.*?)```", text, re.S)
    if match:
        return match.group(1).strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(("select", "with")):
            return stripped
    return None


def intent_classify(state: dict) -> dict:
    response = _llm().invoke(
        [
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": state["question"]},
        ]
    )
    intent = (response.content or "").strip().lower()
    if intent not in ("data_analysis", "knowledge_qa", "clarify"):
        intent = "data_analysis"
    return {"intent": intent}


def plan(state: dict) -> dict:
    response = _llm().invoke(
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": state["question"]},
        ]
    )
    steps = [
        line.strip()
        for line in (response.content or "").splitlines()
        if line.strip() and not line.strip().startswith(("#", "```"))
    ][:5]
    return {"plan": steps or [state["question"]], "current_step": 0, "step_count": 0}


def agent_step(state: dict) -> dict:
    step_count = state.get("step_count", 0)
    if step_count >= settings.max_steps:
        return {"step_count": step_count, "final_answer": "步骤过多，已自动停止，请简化问题后重试。"}

    if state.get("intent") == "knowledge_qa":
        result = run_tool("query_knowledge_base", {"question": state["question"]})
        return {
            "query_result": [{"source": "knowledge", "text": result}],
            "step_count": step_count + 1,
        }

    schema = run_tool("get_schema", {})
    response = _llm().invoke(
        [
            {"role": "system", "content": SQL_SYSTEM},
            {
                "role": "user",
                "content": f"表结构：\n{schema}\n\n问题：{state['question']}\n请生成可执行 SQL。",
            },
        ]
    )
    sql = _extract_sql(response.content or "")
    if not sql:
        return {"errors": ["未能生成 SQL"], "step_count": step_count + 1}

    result = run_tool("query_database", {"sql": sql})
    return {
        "sql": sql,
        "query_result": [{"sql": sql, "result": result}],
        "tool_calls": [
            {"name": "query_database", "arguments": {"sql": sql}, "status": "success"}
        ],
        "step_count": step_count + 1,
    }


def reflect(state: dict) -> dict:
    if state.get("errors"):
        return {"errors": [], "reflect_note": "检测到错误，重试一次"}
    return {"reflect_note": "无需修正"}


def answer(state: dict) -> dict:
    if state.get("final_answer"):
        return {"final_answer": state["final_answer"]}
    context = json.dumps(state.get("query_result", []), ensure_ascii=False, default=str)
    response = _llm().invoke(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": f"问题：{state['question']}\n查询结果：{context[:12_000]}"},
        ]
    )
    return {"final_answer": response.content or "无法生成回答"}


def route_after_intent(state: dict) -> str:
    return state.get("intent", "data_analysis")


def route_after_agent(state: dict) -> str:
    if state.get("errors"):
        return "reflect"
    return "answer"
