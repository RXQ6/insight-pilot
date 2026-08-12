import psycopg

from ..config import settings
from .embed import embed_texts


def retrieve_top_k(question: str, top_k: int = 5) -> list[str]:
    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.document_chunks')")
            table_exists = cur.fetchone()[0] is not None
    if not table_exists:
        return []

    try:
        embedding = embed_texts([question])[0]
    except Exception:
        embedding = None
    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            if embedding is None:
                try:
                    cur.execute(
                        """
                        SELECT content, 0.0 AS score
                        FROM document_chunks
                        WHERE content ILIKE %s
                        ORDER BY id
                        LIMIT %s
                        """,
                        (f"%{question[:50]}%", top_k),
                    )
                except Exception:  # noqa: BLE001
                    return []
            else:
                cur.execute(
                    """
                    SELECT content, 1 - (embedding <=> %s::vector) AS score
                    FROM document_chunks
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (str(embedding), top_k),
                )
            rows = cur.fetchall()
    return [f"[score={round(row[1], 4)}] {row[0]}" for row in rows]
