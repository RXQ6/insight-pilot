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


def _emit_updates(streams: RedisStreams, task_id: str, updates, started: float) -> dict:
    final_answer = None
    chart_spec = None
    usage: list[dict] = []
    interrupted = False
    reason = "需要人工确认"
    for update in updates:
        for node, payload in update.items():
            if node == "__interrupt__":
                interrupted = True
                if isinstance(payload, (list, tuple)) and payload:
                    value = payload[0]
                    if isinstance(value, dict):
                        reason = value.get("reason", reason)
                    elif hasattr(value, "value") and isinstance(value.value, dict):
                        reason = value.value.get("reason", reason)
                continue
            if not isinstance(payload, dict):
                continue
            if node == "agent_step":
                for call in payload.get("tool_calls", []):
                    _publish(streams, task_id, "tool_call", call)
            if node == "answer":
                final_answer = payload.get("final_answer")
                chart_spec = payload.get("chart_spec")
            usage.extend(payload.get("usage", []))

    if final_answer:
        result_payload = {"answer": final_answer}
        if chart_spec:
            result_payload["chartSpec"] = chart_spec
            _publish(streams, task_id, "chart", chart_spec)
        _publish(streams, task_id, "result", result_payload)
        token_in = sum(item.get("prompt_tokens", 0) for item in usage)
        token_out = sum(item.get("completion_tokens", 0) for item in usage)
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
    return {"finished": bool(final_answer), "interrupted": interrupted, "reason": reason}


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
                    updates = graph.stream(
                        Command(resume={"approved": approved}),
                        config={"configurable": {"thread_id": task_id}},
                        stream_mode="updates",
                    )
                    _emit_updates(streams, task_id, updates, started=time.time())
                    streams.ack(settings.task_input_stream, settings.consumer_group, message_id)
                    continue

                task = TaskMessage(**fields)
                started = time.time()
                _publish(streams, task.taskId, "status", "running")
                try:
                    updates = graph.stream(
                        {
                            "question": task.message,
                            "task_id": task.taskId,
                            "session_id": task.sessionId,
                            "history": _load_history(task),
                        },
                        config={"configurable": {"thread_id": task.taskId}},
                        stream_mode="updates",
                    )
                    outcome = _emit_updates(streams, task.taskId, updates, started)
                    if outcome["interrupted"]:
                        _publish(
                            streams,
                            task.taskId,
                            "approval_required",
                            {"taskId": task.taskId, "reason": outcome["reason"]},
                        )
                    elif not outcome["finished"]:
                        _publish(streams, task.taskId, "error", "Agent 未生成回答")
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
