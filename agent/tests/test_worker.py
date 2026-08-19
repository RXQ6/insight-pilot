"""worker.py 事件流与 DLQ 发布逻辑测试（FakeStreams 替代 Redis）。"""

import unittest
from unittest import mock

from insight_agent import worker


class FakeStreams:
    def __init__(self):
        self.published = []

    def publish(self, stream, payload):
        self.published.append((stream, dict(payload)))
        return "id"


def make_stream_items(file_payload=None):
    items = [
        (
            "updates",
            {
                "agent_step": {
                    "tool_calls": [{"name": "query_database", "arguments": {"sql": "s"}, "status": "success"}],
                    "file": file_payload,
                }
            },
        ),
        (
            "updates",
            {
                "answer": {
                    "final_answer": "done answer",
                    "chart_spec": None,
                    "usage": [{"prompt_tokens": 1, "completion_tokens": 1}],
                }
            },
        ),
    ]
    return iter(items)


class TestEmitUpdates(unittest.TestCase):
    def test_publishes_file_event(self):
        streams = FakeStreams()
        file_payload = {
            "filename": "insight-export.csv",
            "mime": "text/csv",
            "rowCount": 1,
            "contentBase64": "eA==",
        }
        state = worker._emit_updates(streams, "t1", make_stream_items(file_payload), started=0)

        types = [payload["type"] for _, payload in streams.published]
        self.assertIn("file", types)
        self.assertIn("result", types)
        self.assertIn("done", types)

        file_event = next(payload for _, payload in streams.published if payload["type"] == "file")
        self.assertIn("insight-export.csv", file_event["content"])

        result_event = next(payload for _, payload in streams.published if payload["type"] == "result")
        self.assertIn("insight-export.csv", result_event["content"])
        self.assertEqual(state["final_answer"], "done answer")

    def test_no_file_when_absent(self):
        streams = FakeStreams()
        worker._emit_updates(streams, "t1", make_stream_items(None), started=0)
        types = [payload["type"] for _, payload in streams.published]
        self.assertNotIn("file", types)

    def test_interrupted_no_result(self):
        streams = FakeStreams()
        items = iter([("updates", {"__interrupt__": [{"reason": "approval required"}]})])
        state = worker._emit_updates(streams, "t1", items, started=0)
        self.assertTrue(state["interrupted"])
        self.assertEqual(state["reason"], "approval required")
        types = [payload["type"] for _, payload in streams.published]
        self.assertNotIn("result", types)


class TestPublishDlq(unittest.TestCase):
    def test_records_error(self):
        streams = FakeStreams()
        worker._publish_dlq(streams, "t-1", "boom")
        self.assertEqual(streams.published[0][0], "task:dlq")
        payload = streams.published[0][1]
        self.assertEqual(payload["taskId"], "t-1")
        self.assertEqual(payload["error"], "boom")
        self.assertTrue(payload["ts"])

    def test_handles_missing_task_id(self):
        streams = FakeStreams()
        worker._publish_dlq(streams, "", "boom")
        self.assertEqual(streams.published[0][1]["taskId"], "unknown")


if __name__ == "__main__":
    unittest.main()
