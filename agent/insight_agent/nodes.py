import json
import re

from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from .config import settings
from .prompts import ANSWER_SYSTEM, CHART_SYSTEM, INTENT_SYSTEM, PLAN_SYSTEM, REACT_SYSTEM, SQL_SYSTEM
from .tools import run_tool
from .tools.export import export_csv, wants_export

# 按 DeepSeek 公开计价粗略折算（每 token 成本，元）
TOKEN_COST = {"prompt": 1e-6, "completion": 2e-6}

BUDGET_MESSAGE = (
    "本次任务的成本预算已用完，已停止继续执行。"
    "请缩小查询范围或提高预算后重试。"
)


def _usage_cost(usage: list[dict]) -> float:
    return sum(
        item.get("prompt_tokens", 0) * TOKEN_COST["prompt"]
        + item.get("completion_tokens", 0) * TOKEN_COST["completion"]
        for item in usage
    )


def _budget_exceeded(state: dict, extra_usage: list[dict]) -> bool:
    """累计已用成本 + 本次新增成本是否超过任务预算（cost_cap_cny）。"""
    cap = state.get("cost_cap_cny")
    if not cap or cap <= 0:
        return False
    total = _usage_cost(state.get("usage") or []) + _usage_cost(extra_usage)
    return total > cap


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
    match = re.search(r"((?:SELECT|WITH)\b.*?;)", text, re.S)
    if match:
        return match.group(1).strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(("select", "with")):
            return stripped
    return None


def _usage(response) -> list[dict]:
    metadata = getattr(response, "usage_metadata", None)
    if not metadata:
        metadata = (getattr(response, "response_metadata", None) or {}).get("token_usage")
    if metadata:
        prompt_tokens = metadata.get("prompt_tokens") or metadata.get("input_tokens") or 0
        completion_tokens = metadata.get("completion_tokens") or metadata.get("output_tokens") or 0
        return [
            {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
            }
        ]
    return []


def _history_text(state: dict) -> str:
    history = state.get("history") or []
    lines = []
    for item in history[-8:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _generate_chart_spec(question: str, context: str) -> tuple[dict | None, list[dict]]:
    response = _llm().invoke(
        [
            {"role": "system", "content": CHART_SYSTEM},
            {"role": "user", "content": f"问题：{question}\n查询结果：{context[:12_000]}"},
        ]
    )
    usage = _usage(response)
    try:
        parsed = json.loads((response.content or "").strip().strip("```json").strip("```"))
    except json.JSONDecodeError:
        return None, usage
    if parsed.get("type") in ("bar", "line", "pie", "scatter") and parsed.get("xAxis") and parsed.get("series"):
        return parsed, usage
    return None, usage


def intent_classify(state: dict) -> dict:
    history = _history_text(state)
    user_content = state["question"]
    if history:
        user_content = f"历史对话：\n{history}\n\n当前问题：{state['question']}"
    response = _llm().invoke(
        [
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": user_content},
        ]
    )
    intent = (response.content or "").strip().lower()
    if intent not in ("data_analysis", "knowledge_qa", "clarify"):
        intent = "data_analysis"
    return {"intent": intent, "usage": _usage(response)}


def plan(state: dict) -> dict:
    history = _history_text(state)
    user_content = state["question"]
    if history:
        user_content = f"历史对话：\n{history}\n\n当前问题：{state['question']}"
    response = _llm().invoke(
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": user_content},
        ]
    )
    steps = [
        line.strip()
        for line in (response.content or "").splitlines()
        if line.strip() and not line.strip().startswith(("#", "```"))
    ][:5]
    return {
        "plan": steps or [state["question"]],
        "current_step": 0,
        "step_count": 0,
        "usage": _usage(response),
    }


def agent_step(state: dict) -> dict:
    max_steps = state.get("max_steps")
    if max_steps is None:
        max_steps = settings.max_steps
    step_count = state.get("step_count", 0)
    if step_count >= max_steps:
        return {
            "step_count": step_count,
            "final_answer": "步骤过多，已自动停止，请简化问题后重试。",
            "errors": [],
        }

    if state.get("intent") == "knowledge_qa":
        try:
            result = run_tool("query_knowledge_base", {"question": state["question"]})
        except Exception as exc:  # noqa: BLE001
            result = f"知识库检索失败：{exc}"
        return {
            "query_result": [{"source": "knowledge", "text": result}],
            "step_count": step_count + 1,
            "usage": [],
        }

    schema = run_tool("get_schema", {"user_id": state.get("user_id", "")})
    if state.get("user_id"):
        schema_rows = json.loads(schema)
        if not schema_rows:
            return {"final_answer": "当前没有可用数据，请先在“数据”页启用示例数据集或上传 CSV。", "usage": []}
    enum_values = run_tool("get_enum_values", {"user_id": state.get("user_id", "")})
    history = _history_text(state)
    fix_hint = state.get("fix_hint")
    plan_steps = state.get("plan") or []
    current_step = state.get("current_step") or 0
    user_content = (
        f"表结构：\n{schema}\n\n字段取值示例：\n{enum_values}\n\n"
        f"问题：{state['question']}\n请生成可执行 SQL。"
    )
    if current_step < len(plan_steps):
        # plan 执行打通：把当前步骤指令注入 SQL 生成
        user_content += (
            f"\n当前执行步骤（第 {current_step + 1}/{len(plan_steps)} 步）：{plan_steps[current_step]}"
        )
    if fix_hint:
        user_content += (
            f"\n\n注意：上次尝试执行失败，请根据以下错误修正后重新生成 SQL"
            f"（必须与上次不同）：\n{fix_hint}"
        )
    if history:
        user_content = f"历史对话：\n{history}\n\n{user_content}"
    response = _llm().invoke(
        [
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": user_content},
        ]
    )
    usage = _usage(response)
    if _budget_exceeded(state, usage):
        return {"final_answer": BUDGET_MESSAGE, "usage": usage}

    sql = _extract_sql(response.content or "")
    if not sql:
        return {"errors": ["未能生成 SQL"], "step_count": step_count + 1, "usage": usage}

    needs_approval = (
        any(keyword in state["question"] for keyword in ("导出", "全表", "所有字段所有行", "全部记录"))
        or (
            re.search(r"\bselect\s+\*\b", sql, re.I)
            and not re.search(r"\blimit\b", sql, re.I)
        )
    )
    if needs_approval:
        decision = interrupt({"tool": "query_database", "reason": "该查询可能返回全表数据，需要人工确认后执行"})
        if isinstance(decision, dict) and decision.get("approved") is False:
            return {
                "final_answer": "查询已被拒绝，未执行任何操作。",
                "step_count": step_count + 1,
                "usage": usage,
            }

    result = run_tool("query_database", {"sql": sql, "user_id": state.get("user_id", "")})
    if isinstance(result, str) and result.startswith("错误"):
        # 工具层拦截/执行失败：进入 errors 交给 reflect 纠错后重试
        return {
            "errors": [result[:500]],
            "sql": sql,
            "tool_calls": [
                {"name": "query_database", "arguments": {"sql": sql}, "status": "error", "output": result[:500]}
            ],
            "step_count": step_count + 1,
            "usage": usage,
        }

    # ReAct 决策循环：LLM 判断是否需要继续调用工具（execute_python/补充查询等）
    loop = _react_loop(state, result, sql)
    tool_calls = loop["tool_calls"]
    file_payload = None
    if wants_export(state["question"]):
        try:
            file_payload = json.loads(export_csv(sql, user_id=state.get("user_id", "")))
            tool_calls.append({"name": "export_csv", "arguments": {"sql": sql}, "status": "success"})
        except Exception as exc:  # noqa: BLE001
            tool_calls.append({"name": "export_csv", "arguments": {"sql": sql}, "status": "error", "output": str(exc)})
    return {
        "sql": sql,
        "query_result": loop["query_result"],
        "file": file_payload,
        "tool_calls": tool_calls,
        "step_count": loop["step_count"],
        "current_step": (state.get("current_step") or 0) + 1,
        "usage": usage + loop["usage"],
    }


def verify(state: dict) -> dict:
    """结果校验节点：检查查询结果是否存在硬错误（错误前缀/无结果），空结果仅提示不阻断。

    校验不通过时返回 errors 交给 reflect 纠错重试，避免"模型说什么就返回什么"。
    """
    query_result = state.get("query_result") or []
    issues = []
    if not query_result:
        issues.append("没有任何查询结果，请重新尝试")
    else:
        for item in query_result[-3:]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("result", ""))
            if text.startswith("错误"):
                issues.append(text[:200])
            elif "truncated" in text and '"truncated": true' in text:
                issues.append("查询结果被截断（超过行数上限），请缩小范围重试")
    if issues:
        return {"errors": issues, "verify_note": "校验未通过：" + "；".join(issues)}
    return {"verify_note": "校验通过", "errors": []}


def _parse_action(text: str) -> dict | None:
    """解析 ReAct 循环中 LLM 输出的动作 JSON：{"action": "tool_call"|"finish", ...}"""
    try:
        cleaned = (text or "").strip().strip("```json").strip("```").strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and parsed.get("action") in ("tool_call", "finish"):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


def _react_loop(state: dict, first_result: str, sql: str) -> dict:
    """ReAct 决策循环：LLM 自主决定继续调用工具还是 finish。

    返回 {"query_result", "tool_calls", "usage", "step_count"}。
    首轮查询结果已进入循环上下文；循环受 tool_loop_limit / max_steps / 预算三重兜底。
    """
    max_steps = state.get("max_steps")
    if max_steps is None:
        max_steps = settings.max_steps
    step_count = state.get("step_count", 0) + 1  # 首轮查询占 1 步
    query_result = [{"sql": sql, "result": first_result}]
    tool_calls = [{"name": "query_database", "arguments": {"sql": sql}, "status": "success"}]
    usage: list = []
    history = _history_text(state)
    observations = f"问题：{state['question']}"
    if history:
        observations += f"\n历史对话：\n{history}"
    observations += f"\n\n首次查询 SQL：\n{sql}\n\n查询结果：\n{first_result[:4_000]}"

    for _ in range(settings.tool_loop_limit):
        if step_count >= max_steps:
            break
        response = _llm().invoke(
            [
                {"role": "system", "content": REACT_SYSTEM},
                {"role": "user", "content": observations},
            ]
        )
        usage += _usage(response)
        if _budget_exceeded(state, usage):
            break
        action = _parse_action(response.content or "")
        if not action or action.get("action") == "finish":
            break

        tool = str(action.get("tool") or "")
        arguments = action.get("arguments") or {}
        try:
            tool_result = run_tool(tool, arguments)
        except Exception as exc:  # noqa: BLE001
            tool_result = f"工具执行失败：{exc}"
        text_result = str(tool_result)
        status = "success" if not text_result.startswith("错误") else "error"
        tool_calls.append(
            {"name": tool, "arguments": arguments, "status": status, "output": text_result[:200]}
        )
        query_result.append(
            {"tool": tool, "arguments": arguments, "result": text_result[: settings.max_tool_output_chars]}
        )
        observations += f"\n\n[工具 {tool} 执行结果]\n{text_result[:4_000]}"
        step_count += 1

    return {
        "query_result": query_result,
        "tool_calls": tool_calls,
        "usage": usage,
        "step_count": step_count,
    }


def reflect(state: dict) -> dict:
    """质检节点：把上次的 SQL、执行错误组装成 fix_hint 回喂给 agent_step 重新生成。"""
    errors = state.get("errors") or []
    if not errors:
        return {"reflect_note": "无需修正", "fix_hint": None}

    parts = []
    last_sql = state.get("sql")
    if last_sql:
        parts.append(f"上次 SQL：{last_sql}")
    query_result = state.get("query_result") or []
    if query_result and isinstance(query_result[-1], dict):
        last_result = query_result[-1].get("result")
        if isinstance(last_result, str) and last_result.startswith("错误"):
            parts.append(f"执行结果：{last_result[:500]}")
    parts.append("错误：" + "；".join(str(error)[:200] for error in errors))
    hint = "\n".join(parts) if parts else "上次尝试失败，请换一种写法重试"
    return {"errors": [], "reflect_note": "检测到错误，已带上错误信息重新生成 SQL", "fix_hint": hint}


def answer(state: dict) -> dict:
    if state.get("final_answer"):
        return {"final_answer": state["final_answer"], "chart_spec": state.get("chart_spec"), "usage": []}
    context = json.dumps(state.get("query_result", []), ensure_ascii=False, default=str)
    history = _history_text(state)
    user_content = f"问题：{state['question']}\n查询结果：{context[:12_000]}"
    if history:
        user_content = f"历史对话：\n{history}\n\n{user_content}"
    response = _llm().invoke(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": user_content},
        ]
    )
    usage = _usage(response)
    chart_spec = None
    chart_usage = []
    if state.get("query_result") and not _budget_exceeded(state, usage):
        chart_spec, chart_usage = _generate_chart_spec(state["question"], context)
    return {
        "final_answer": response.content or "无法生成回答",
        "chart_spec": chart_spec,
        "usage": usage + chart_usage,
    }


def route_after_intent(state: dict) -> str:
    return state.get("intent", "data_analysis")


def route_after_agent(state: dict) -> str:
    # final_answer 已生成则直接收尾，避免残留 errors 导致 reflect 死循环
    if state.get("final_answer"):
        return "answer"
    if state.get("errors"):
        return "reflect"
    # plan 执行打通：还有未执行的步骤则继续 agent_step
    current = state.get("current_step") or 0
    if current < len(state.get("plan") or []):
        return "agent_step"
    return "verify"


def route_after_verify(state: dict) -> str:
    if state.get("errors"):
        return "reflect"
    return "answer"
