import json

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


def get_schema(table: str | None = None) -> str:
    with _connect() as conn:
        with conn.cursor() as cur:
            if table:
                cur.execute(
                    """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
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
    payload = [
        {"table": row[0], "column": row[1], "type": row[2], "nullable": row[3]} for row in rows
    ]
    return json.dumps(payload, ensure_ascii=False)


def query_database(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    lowered = sql.lower()
    if any(keyword in lowered for keyword in FORBIDDEN_KEYWORDS):
        return "错误：只允许 SELECT / WITH 只读查询"
    if ";" in sql:
        return "错误：禁止多条语句"

    options = f"-c statement_timeout={settings.sql_timeout_seconds * 1000}"
    with _connect(options=options) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql)
            columns = [desc.name for desc in cur.description] if cur.description else []
            rows = cur.fetchmany(settings.query_row_limit)

    payload = {
        "columns": columns,
        "rows": rows,
        "truncated": len(rows) >= settings.query_row_limit,
    }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text[: settings.max_tool_output_chars]


def get_enum_values() -> str:
    queries = [
        ("orders.status", "SELECT DISTINCT status FROM orders"),
        ("products.category", "SELECT DISTINCT category FROM products"),
        ("customers.region", "SELECT DISTINCT region FROM customers"),
    ]
    payload = {}
    with _connect() as conn:
        with conn.cursor() as cur:
            for key, sql in queries:
                cur.execute(sql)
                payload[key] = [row[0] for row in cur.fetchall()]
    return json.dumps(payload, ensure_ascii=False)


def _connect(options: str | None = None):
    dsn = settings.postgres_readonly_dsn or settings.postgres_dsn
    return psycopg.connect(dsn, connect_timeout=5, options=options)
