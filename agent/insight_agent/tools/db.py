import json
import re

import psycopg

from ..config import settings

FORBIDDEN_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "grant",
    "revoke",
    "create",
)

SHARED_DEMO_TABLES = {"customers", "products", "orders", "order_items"}


def _connect(options: str | None = None):
    dsn = settings.postgres_readonly_dsn or settings.postgres_dsn
    return psycopg.connect(dsn, connect_timeout=5, options=options)


def _user_context(user_id: str) -> tuple[set[str], dict[str, str]]:
    shared = set()
    dataset_names = {}
    if not user_id:
        return shared, dataset_names
    try:
        uid = int(user_id)
    except ValueError:
        return shared, dataset_names
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT demo_enabled FROM users WHERE id = %s", (uid,))
            row = cur.fetchone()
            if row and row[0]:
                shared = set(SHARED_DEMO_TABLES)
            cur.execute("SELECT name, table_name FROM datasets WHERE user_id = %s", (uid,))
            for name, table in cur.fetchall():
                dataset_names[table] = name
    return shared, dataset_names


def get_schema(table: str | None = None, user_id: str = "") -> str:
    shared, dataset_names = _user_context(user_id)
    with _connect() as conn:
        with conn.cursor() as cur:
            if table:
                cur.execute(
                    """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY table_name, ordinal_position
                    """,
                    (table,),
                )
            else:
                cur.execute(
                    """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
            rows = cur.fetchall()

    payload = []
    for row in rows:
        table_name, column_name, data_type, is_nullable = row
        if user_id:
            if table_name in shared:
                payload.append({"table": table_name, "dataset": "demo", "column": column_name, "type": data_type, "nullable": is_nullable})
            elif table_name in dataset_names:
                payload.append({"table": table_name, "dataset": dataset_names[table_name], "column": column_name, "type": data_type, "nullable": is_nullable})
        else:
            dataset_label = "demo" if table_name in SHARED_DEMO_TABLES else ""
            payload.append({"table": table_name, "dataset": dataset_label, "column": column_name, "type": data_type, "nullable": is_nullable})
    return json.dumps(payload, ensure_ascii=False)


def get_enum_values(user_id: str = "") -> str:
    shared, _ = _user_context(user_id)
    queries = [
        ("orders.status", "SELECT DISTINCT status FROM orders"),
        ("products.category", "SELECT DISTINCT category FROM products"),
        ("customers.region", "SELECT DISTINCT region FROM customers"),
    ]
    payload = {}
    with _connect() as conn:
        with conn.cursor() as cur:
            for key, sql in queries:
                table_name = key.split(".")[0]
                if user_id and table_name not in shared:
                    continue
                cur.execute(sql)
                payload[key] = [row[0] for row in cur.fetchall()]
    return json.dumps(payload, ensure_ascii=False)


def fetch_rows(sql: str, user_id: str = "") -> tuple[list[str], list[list]]:
    """执行只读查询，返回 (列名, 行数据)。带关键字拦截、用户表隔离与行数上限。"""
    sql = sql.strip().rstrip(";").strip()
    lowered = sql.lower()
    if any(keyword in lowered for keyword in FORBIDDEN_KEYWORDS):
        raise PermissionError("只允许 SELECT / WITH 只读查询")
    if ";" in sql:
        raise ValueError("禁止多条语句")
    if user_id:
        shared, dataset_names = _user_context(user_id)
        for name in re.findall(r"(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.I):
            if name in SHARED_DEMO_TABLES and name not in shared:
                raise PermissionError("请先在数据页启用示例数据集")
            if name.startswith("dataset_") and name not in dataset_names:
                raise PermissionError("无权访问该数据表")

    options = f"-c statement_timeout={settings.sql_timeout_seconds * 1000}"
    with _connect(options=options) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql)
            columns = [desc.name for desc in cur.description] if cur.description else []
            rows = cur.fetchmany(settings.query_row_limit)
    return columns, rows


def query_database(sql: str, user_id: str = "") -> str:
    try:
        columns, rows = fetch_rows(sql, user_id)
    except (PermissionError, ValueError) as exc:
        return f"错误：{exc}"

    payload = {
        "columns": columns,
        "rows": rows,
        "truncated": len(rows) >= settings.query_row_limit,
    }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text[: settings.max_tool_output_chars]
