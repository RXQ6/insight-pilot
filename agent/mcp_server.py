"""MCP server exposing InsightPilot tools for external Agent clients."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP

from insight_agent.tools.chart import generate_chart
from insight_agent.tools.db import get_enum_values, get_schema, query_database
from insight_agent.tools.knowledge import query_knowledge_base
from insight_agent.tools.python_sandbox import execute_python

mcp = FastMCP("insight-pilot")


@mcp.tool(name="get_schema", description="获取数据库表结构")
def get_schema_tool(table: str | None = None) -> str:
    return get_schema(table)


@mcp.tool(name="get_enum_values", description="获取状态、品类、区域等字段取值示例")
def get_enum_values_tool() -> str:
    return get_enum_values()


@mcp.tool(name="query_database", description="执行只读 SQL 查询")
def query_database_tool(sql: str) -> str:
    return query_database(sql)


@mcp.tool(name="execute_python", description="在沙箱中执行 Python 分析代码")
def execute_python_tool(code: str) -> str:
    return execute_python(code)


@mcp.tool(name="generate_chart", description="生成 ECharts 图表 spec")
def generate_chart_tool(chart_type: str, x: list, y: list, title: str = "") -> str:
    return generate_chart(chart_type, x, y, title)


@mcp.tool(name="query_knowledge_base", description="检索数据说明与运维知识库")
def query_knowledge_base_tool(question: str) -> str:
    return query_knowledge_base(question)


if __name__ == "__main__":
    mcp.run()
