"""nodes.py 核心逻辑测试：预算强制、max_steps、审批拒绝、导出触发、reflect 纠错。
unittest 风格（mock LLM/工具/中断），pytest 亦兼容，不依赖外部服务。"""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from insight_agent import nodes


class FakeLLM:
    def __init__(self, content, usage=None):
        self.content = content
        self.usage = usage or {"prompt_tokens": 10, "completion_tokens": 5}
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return SimpleNamespace(content=self.content, usage_metadata=self.usage)


SCHEMA = json.dumps([{"table": "orders", "column": "id", "type": "integer", "nullable": False}])
ENUM = json.dumps({"orders.status": ["completed", "pending"]})


def make_state(**overrides):
    state = {
        "question": "4月订单总数",
        "task_id": "t1",
        "session_id": "s1",
        "history": [],
        "user_id": "",
        "intent": "data_analysis",
        "plan": [],
        "current_step": 0,
        "step_count": 0,
        "max_steps": None,
        "cost_cap_cny": None,
        "sql": None,
        "query_result": None,
        "chart_spec": None,
        "file": None,
        "final_answer": None,
        "errors": [],
        "tool_calls": [],
        "usage": [],
        "reflect_note": None,
        "fix_hint": None,
    }
    state.update(overrides)
    return state


def patch_run_tool(query_result='{"columns": ["cnt"], "rows": [[10]]}'):
    def fake_run_tool(name, arguments=None, **kwargs):
        if name == "get_schema":
            return SCHEMA
        if name == "get_enum_values":
            return ENUM
        if name == "query_database":
            return query_result
        raise AssertionError(f"unexpected tool: {name}")

    return mock.patch.object(nodes, "run_tool", side_effect=fake_run_tool)


class TestBudgetHelpers(unittest.TestCase):
    def test_usage_cost(self):
        self.assertEqual(nodes._usage_cost([{"prompt_tokens": 1000, "completion_tokens": 0}]), 0.001)
        self.assertEqual(nodes._usage_cost([]), 0.0)

    def test_budget_not_exceeded(self):
        self.assertFalse(
            nodes._budget_exceeded(
                {"cost_cap_cny": 0.2, "usage": []},
                [{"prompt_tokens": 100, "completion_tokens": 100}],
            )
        )

    def test_budget_exceeded_cumulative(self):
        self.assertTrue(
            nodes._budget_exceeded(
                {"cost_cap_cny": 0.0001, "usage": [{"prompt_tokens": 1000, "completion_tokens": 0}]},
                [],
            )
        )

    def test_cap_zero_means_unlimited(self):
        self.assertFalse(
            nodes._budget_exceeded(
                {"cost_cap_cny": 0, "usage": []},
                [{"prompt_tokens": 10**6, "completion_tokens": 0}],
            )
        )


class TestAgentStep(unittest.TestCase):
    def test_budget_exceeded_stops(self):
        llm = FakeLLM("```sql\nSELECT count(*) FROM orders\n```", usage={"prompt_tokens": 100_000, "completion_tokens": 0})
        with mock.patch.object(nodes, "_llm", return_value=llm), patch_run_tool():
            out = nodes.agent_step(make_state(cost_cap_cny=0.001))
        self.assertIn(nodes.BUDGET_MESSAGE, out["final_answer"])
        self.assertIsNone(out.get("query_result"))

    def test_max_steps_from_state(self):
        with mock.patch.object(
            nodes, "_llm", side_effect=AssertionError("LLM must not be called")
        ):
            out = nodes.agent_step(make_state(max_steps=0))
        self.assertIn("步骤过多", out["final_answer"])

    def test_approval_rejected_skips_query(self):
        with mock.patch.object(nodes, "interrupt", return_value={"approved": False}), mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("```sql\nSELECT * FROM orders\n```")
        ):

            def fake_run_tool(name, arguments=None, **kwargs):
                if name in ("get_schema", "get_enum_values"):
                    return SCHEMA if name == "get_schema" else ENUM
                raise AssertionError("query_database must not run after rejection")

            with mock.patch.object(nodes, "run_tool", side_effect=fake_run_tool):
                out = nodes.agent_step(make_state(question="导出全部订单"))
        self.assertIn("拒绝", out["final_answer"])
        self.assertIsNone(out.get("query_result"))
        self.assertIsNone(out.get("file"))

    def test_approval_accepted_executes(self):
        with mock.patch.object(nodes, "interrupt", return_value={"approved": True}), mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("```sql\nSELECT * FROM orders LIMIT 10\n```")
        ), patch_run_tool(query_result='{"columns": ["id"], "rows": [[1]]}'):
            out = nodes.agent_step(make_state(question="导出全部订单"))
        self.assertIsNotNone(out.get("query_result"))
        self.assertEqual(out["tool_calls"][0]["name"], "query_database")

    def test_export_file_emitted(self):
        file_json = json.dumps(
            {"filename": "insight-export.csv", "mime": "text/csv", "rowCount": 1, "contentBase64": "eA=="}
        )
        with mock.patch.object(nodes, "interrupt", return_value={"approved": True}), mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("```sql\nSELECT region, sum(amount) FROM orders GROUP BY region\n```")
        ), patch_run_tool(query_result='{"columns": ["region"], "rows": [["华东"]]}'), mock.patch.object(
            nodes, "export_csv", return_value=file_json
        ):
            out = nodes.agent_step(make_state(question="导出各区域销售额"))
        self.assertEqual(out["file"]["filename"], "insight-export.csv")
        self.assertIn("export_csv", [call["name"] for call in out["tool_calls"]])

    def test_no_export_without_keyword(self):
        with mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("```sql\nSELECT count(*) FROM orders\n```")
        ), patch_run_tool():
            out = nodes.agent_step(make_state(question="4月订单总数"))
        self.assertIsNone(out["file"])
        self.assertNotIn("export_csv", [call["name"] for call in out["tool_calls"]])

    def test_tool_error_enters_errors(self):
        with mock.patch.object(nodes, "interrupt", return_value={"approved": True}), mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("```sql\nSELECT * FROM orders\n```")
        ), patch_run_tool(query_result="错误：只允许 SELECT / WITH 只读查询"):
            out = nodes.agent_step(make_state(question="4月订单总数"))
        self.assertEqual(out["errors"], ["错误：只允许 SELECT / WITH 只读查询"])
        self.assertEqual(out["tool_calls"][0]["status"], "error")
        self.assertIsNone(out.get("query_result"))

    def test_fix_hint_feeds_into_prompt(self):
        llm = FakeLLM("```sql\nSELECT count(*) FROM orders\n```")
        with mock.patch.object(nodes, "_llm", return_value=llm), patch_run_tool():
            nodes.agent_step(make_state(question="4月订单总数", fix_hint="上次 SQL：SELECT * FROM orders\n错误：列不存在"))
        joined = "".join(m["content"] for m in llm.last_messages if m["role"] == "user")
        self.assertIn("上次尝试执行失败", joined)
        self.assertIn("上次 SQL", joined)


class TestReflect(unittest.TestCase):
    def test_builds_fix_hint_from_errors(self):
        state = make_state(
            errors=["错误：列 x 不存在"],
            sql="SELECT x FROM orders",
            query_result=[{"sql": "SELECT x FROM orders", "result": "错误：列 x 不存在"}],
        )
        out = nodes.reflect(state)
        self.assertEqual(out["errors"], [])
        self.assertIn("SELECT x FROM orders", out["fix_hint"])
        self.assertIn("列 x 不存在", out["fix_hint"])

    def test_no_errors_returns_none_hint(self):
        out = nodes.reflect(make_state())
        self.assertIsNone(out["fix_hint"])
        self.assertEqual(out["reflect_note"], "无需修正")


class TestAnswer(unittest.TestCase):
    def test_budget_skips_chart(self):
        llm = FakeLLM("结论：总数为 10", usage={"prompt_tokens": 5000, "completion_tokens": 1000})
        with mock.patch.object(nodes, "_llm", return_value=llm), mock.patch.object(
            nodes, "_generate_chart_spec", return_value=({"type": "bar", "xAxis": ["a"], "series": [1]}, [])
        ):
            out = nodes.answer(make_state(cost_cap_cny=0.001, query_result=[{"sql": "s", "result": "x"}]))
        self.assertIn("总数为 10", out["final_answer"])
        self.assertIsNone(out["chart_spec"])

    def test_generates_chart_within_budget(self):
        with mock.patch.object(
            nodes, "_llm", return_value=FakeLLM("结论：总数为 10")
        ), mock.patch.object(
            nodes, "_generate_chart_spec", return_value=({"type": "bar", "xAxis": ["a"], "series": [1]}, [])
        ):
            out = nodes.answer(make_state(cost_cap_cny=0.2, query_result=[{"sql": "s", "result": "x"}]))
        self.assertEqual(out["chart_spec"]["type"], "bar")


if __name__ == "__main__":
    unittest.main()
