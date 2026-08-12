import subprocess

from ..config import settings


def execute_python(code: str) -> str:
    if len(code) > 20_000:
        return "错误：代码过长"
    try:
        result = subprocess.run(
            [settings.sandbox_python, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return "错误：执行超时"

    output = result.stdout[-settings.max_tool_output_chars :] if result.stdout else ""
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr[-4_000:]
    return output or "(无输出)"
