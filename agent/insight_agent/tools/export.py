"""查询结果导出：把只读 SQL 的结果转成 CSV 文件内容（base64），供前端直接下载。"""

import base64
import csv
import io
import json

from .db import fetch_rows

EXPORT_KEYWORDS = ("导出", "下载", "csv", "excel", "xlsx")


def wants_export(question: str) -> bool:
    """判断用户是否要求导出文件。"""
    lowered = question.lower()
    return any(keyword in lowered for keyword in EXPORT_KEYWORDS)


def export_csv(sql: str, user_id: str = "") -> str:
    """执行只读查询并生成 CSV，返回 JSON：
    {"filename", "mime", "rowCount", "contentBase64"}。
    """
    columns, rows = fetch_rows(sql, user_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    csv_text = buffer.getvalue()

    content_base64 = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    return json.dumps(
        {
            "filename": "insight-export.csv",
            "mime": "text/csv",
            "rowCount": len(rows),
            "contentBase64": content_base64,
        },
        ensure_ascii=False,
    )
