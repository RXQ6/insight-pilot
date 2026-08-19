"""诊断单个评测用例：打印 Agent 生成的 SQL 与判定差异，用于失败根因分析。

用法：
    .venv/Scripts/python scripts/diagnose_case.py sql_single_022
    .venv/Scripts/python scripts/diagnose_case.py time_trend_003
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insight_agent.graph import build_graph
from insight_agent.tools import run_tool

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def main(case_id: str) -> None:
    cases = json.loads((DATA_DIR / "eval_cases.json").read_text(encoding="utf-8"))
    case = next((c for c in cases if c["id"] == case_id), None)
    if case is None:
        print(f"未找到用例 {case_id}")
        return

    graph = build_graph()
    result = graph.invoke(
        {"question": case["question"], "task_id": f"diag_{case_id}", "session_id": "diag"},
        config={"configurable": {"thread_id": f"diag_{case_id}"}},
    )
    sql = result.get("sql")
    answer = result.get("final_answer")

    print(f"用例: {case_id} ({case['type']})")
    print(f"问题: {case['question']}")
    print(f"期望: {case.get('expected_sql')}")
    print(f"生成: {sql}")
    print(f"回答: {(answer or '')[:200]}")

    if sql and case.get("expected_sql"):
        try:
            expected = json.loads(run_tool("query_database", {"sql": case["expected_sql"]}))
            actual = json.loads(run_tool("query_database", {"sql": sql}))
            print(f"期望行数: {len(expected.get('rows', []))}  实际行数: {len(actual.get('rows', []))}")
            print(f"期望前5行: {expected.get('rows', [])[:5]}")
            print(f"实际前5行: {actual.get('rows', [])[:5]}")
        except Exception as exc:  # noqa: BLE001
            print(f"执行对比失败: {exc}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sql_single_022")
