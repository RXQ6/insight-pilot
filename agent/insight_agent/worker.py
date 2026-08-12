import json
import logging
import time

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


def run_worker() -> None:
    streams = RedisStreams()
    streams.ensure_group(settings.task_input_stream, settings.consumer_group)
    graph = build_graph()
    logger.info("InsightPilot agent worker started")

    while True:
        for message_id, fields in streams.consume(
            settings.task_input_stream, settings.consumer_group, "worker-1"
        ):
            task = TaskMessage(**fields)
            started = time.time()
            _publish(streams, task.taskId, "status", "running")
            try:
                final_answer = None
                for update in graph.stream(
                    {
                        "question": task.message,
                        "task_id": task.taskId,
                        "session_id": task.sessionId,
                    },
                    config={"configurable": {"thread_id": task.taskId}},
                    stream_mode="updates",
                ):
                    for node, payload in update.items():
                        if node == "agent_step":
                            for call in payload.get("tool_calls", []):
                                _publish(streams, task.taskId, "tool_call", call)
                        if node == "answer":
                            final_answer = payload.get("final_answer")

                if final_answer:
                    _publish(streams, task.taskId, "result", {"answer": final_answer})
                    _publish(
                        streams,
                        task.taskId,
                        "done",
                        {"latencyMs": int((time.time() - started) * 1000)},
                    )
                else:
                    _publish(streams, task.taskId, "error", "Agent 未生成回答")
            except Exception as exc:  # noqa: BLE001
                logger.exception("task %s failed", task.taskId)
                _publish(streams, task.taskId, "error", str(exc))
            finally:
                streams.ack(settings.task_input_stream, settings.consumer_group, message_id)


if __name__ == "__main__":
    run_worker()
