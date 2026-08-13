import re

import psycopg

from ..config import settings
from .embed import embed_texts


def _keyword_terms(question: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", question)
    terms = set()
    for token in tokens:
        if len(token) >= 2:
            terms.add(token)
        for index in range(len(token) - 1):
            terms.add(token[index : index + 2])
    if not terms:
        terms.add(question[:20])
    return list(terms)


def retrieve_top_k(question: str, top_k: int = 5) -> list[str]:
    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.document_chunks')")
            table_exists = cur.fetchone()[0] is not None
    if not table_exists:
        return []

    if settings.embedding_enabled:
        try:
            embedding = embed_texts([question])[0]
        except Exception:
            embedding = None
    else:
        embedding = None

    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            if embedding is None:
                patterns = [f"%{term}%" for term in _keyword_terms(question)]
                try:
                    cur.execute(
                        """
                        SELECT content, 0.0 AS score
                        FROM document_chunks
                        WHERE content ILIKE ANY(%s)
                        ORDER BY id
                        LIMIT %s
                        """,
                        (patterns, top_k),
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

