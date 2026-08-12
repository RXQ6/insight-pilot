import json

ALLOWED_TYPES = {"bar", "line", "pie", "scatter"}


def generate_chart(chart_type: str, x: list, y: list, title: str = "") -> str:
    if chart_type not in ALLOWED_TYPES:
        return "错误：不支持的图表类型"
    spec = {"type": chart_type, "title": title, "xAxis": x, "series": y}
    return json.dumps(spec, ensure_ascii=False)
