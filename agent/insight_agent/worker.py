import json
import logging
import time

from langgraph.types import Command

from .config import settings
from .graph import build_graph
from .models import TaskMessage
from .redis_client import RedisStreams

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _publish(streams: RedisStreams, task_id: str, event_type: str, content) -> None:
    streams.publish(
        settings.task_result_stream,
        {
            "taskId": task_id,
            "type": event_type,
            "content": json.dumps(content, ensure_ascii=False, default=str),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


def _load_history(task: TaskMessage) -> list[dict]:
    if not task.history:
        return []
    try:
        parsed = json.loads(task.history)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _handle_item(streams: RedisStreams, task_id: str, item, state: dict) -> dict:
    if isinstance(item, tuple) and len(item) == 2:
        mode, payload = item
        if mode == "messages" and isinstance(payload, (list, tuple)) and payload:
            chunk = payload[0]
            metadata = payload[1] if len(payload) > 1 else {}
            node = (metadata or {}).get("langgraph_node") if isinstance(metadata, dict) else None
            if node == "answer":
                text = getattr(chunk, "content", "") or ""
                if text:
                    _publish(streams, task_id, "token", text)
            return state
        if mode == "updates":
            item = payload
        else:
            return state

    for node, payload in item.items():
        if node == "__interrupt__":
            state["interrupted"] = True
            if isinstance(payload, (list, tuple)) and payload:
                value = payload[0]
                if isinstance(value, dict):
                    state["reason"] = value.get("reason", state["reason"])
                elif hasattr(value, "value") and isinstance(value.value, dict):
                    state["reason"] = value.value.get("reason", state["reason"])
            continue
        if not isinstance(payload, dict):
            continue
        if node == "agent_step":
            for call in payload.get("tool_calls", []):
                _publish(streams, task_id, "tool_call", call)
        if node == "answer":
            state["final_answer"] = payload.get("final_answer")
            state["chart_spec"] = payload.get("chart_spec")
        state["usage"].extend(payload.get("usage", []))
    return state


def _emit_updates(streams: RedisStreams, task_id: str, stream, started: float) -> dict:
    state = {
        "final_answer": None,
        "chart_spec": None,
        "usage": [],
        "interrupted": False,
        "reason": "approval required",
    }
    for item in stream:
        _handle_item(streams, task_id, item, state)

    if state["final_answer"]:
        result_payload = {"answer": state["final_answer"]}
        if state["chart_spec"]:
            result_payload["chartSpec"] = state["chart_spec"]
            _publish(streams, task_id, "chart", state["chart_spec"])
        _publish(streams, task_id, "result", result_payload)
        token_in = sum(item.get("prompt_tokens", 0) for item in state["usage"])
        token_out = sum(item.get("completion_tokens", 0) for item in state["usage"])
        _publish(
            streams,
            task_id,
            "done",
            {
                "latencyMs": int((time.time() - started) * 1000),
                "tokenIn": token_in,
                "tokenOut": token_out,
                "costCny": round(token_in * 0.000001 + token_out * 0.000002, 6),
            },
        )
    return state


def run_worker() -> None:
    streams = RedisStreams()
    streams.ensure_group(settings.task_input_stream, settings.consumer_group)
    graph = build_graph()
    logger.info("InsightPilot agent worker started")

    while True:
        for message_id, fields in streams.consume(
            settings.task_input_stream, settings.consumer_group, "worker-1"
        ):
            try:
                if fields.get("action") == "resume":
                    task_id = fields["taskId"]
                    approved = str(fields.get("approved", "false")).lower() == "true"
                    _publish(streams, task_id, "status", "running")
                    stream = graph.stream(
                        Command(resume={"approved": approved}),
                        config={"configurable": {"thread_id": task_id}},
                        stream_mode=["updates", "messages"],
                    )
                    _emit_updates(streams, task_id, stream, started=time.time())
                    streams.ack(settings.task_input_stream, settings.consumer_group, message_id)
                    continue

                task = TaskMessage(**fields)
                started = time.time()
                _publish(streams, task.taskId, "status", "running")
                try:
                    stream = graph.stream(
                        {
                            "question": task.message,
                            "task_id": task.taskId,
                            "session_id": task.sessionId,
                            "history": _load_history(task),
                            "user_id": task.userId,
                        },
                        config={"configurable": {"thread_id": task.taskId}},
                        stream_mode=["updates", "messages"],
                    )
                    outcome = _emit_updates(streams, task.taskId, stream, started)
                    if outcome["interrupted"]:
                        _publish(
                            streams,
                            task.taskId,
                            "approval_required",
                            {"taskId": task.taskId, "reason": outcome["reason"]},
                        )
                    elif not outcome["final_answer"]:
                        _publish(streams, task.taskId, "error", "Agent did not generate an answer")
                except Exception as exc:  # noqa: BLE001
                    logger.exception("task %s failed", task.taskId)
                    _publish(streams, task.taskId, "error", str(exc))
                finally:
                    streams.ack(settings.task_input_stream, settings.consumer_group, message_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("worker loop error")
                try:
                    streams.ack(settings.task_input_stream, settings.consumer_group, message_id)
                except Exception:
                    pass


if __name__ == "__main__":
    run_worker()
