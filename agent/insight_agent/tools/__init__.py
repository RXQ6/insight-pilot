from dataclasses import dataclass
from typing import Callable

from .chart import generate_chart
from .db import get_enum_values, get_schema, query_database
from .export import export_csv
from .knowledge import query_knowledge_base
from .python_sandbox import execute_python


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., str]


TOOLS: list[Tool] = [
    Tool(
        name="get_schema",
        description="获取数据库表结构",
        parameters={"table": {"type": "string", "description": "表名，可省略"}},
        handler=get_schema,
    ),
    Tool(
        name="query_database",
        description="执行只读 SQL 查询",
        parameters={"sql": {"type": "string", "description": "SELECT / WITH 语句"}},
        handler=query_database,
    ),
    Tool(
        name="get_enum_values",
        description="获取状态、品类、区域等字段的取值示例",
        parameters={},
        handler=get_enum_values,
    ),
    Tool(
        name="execute_python",
        description="在沙箱中执行 Python 分析代码",
        parameters={"code": {"type": "string", "description": "Python 代码"}},
        handler=execute_python,
    ),
    Tool(
        name="generate_chart",
        description="生成 ECharts 图表 spec",
        parameters={
            "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter"]},
            "x": {"type": "array"},
            "y": {"type": "array"},
            "title": {"type": "string"},
        },
        handler=generate_chart,
    ),
    Tool(
        name="export_csv",
        description="将只读 SQL 的查询结果导出为 CSV 下载文件",
        parameters={"sql": {"type": "string", "description": "SELECT / WITH 语句"}},
        handler=export_csv,
    ),
    Tool(
        name="query_knowledge_base",
        description="检索数据说明与运维知识库",
        parameters={"question": {"type": "string"}},
        handler=query_knowledge_base,
    ),
]

TOOL_MAP = {tool.name: tool for tool in TOOLS}


def run_tool(name: str, arguments: dict) -> str:
    tool = TOOL_MAP.get(name)
    if tool is None:
        return f"错误：未知工具 {name}"
    return tool.handler(**arguments)
