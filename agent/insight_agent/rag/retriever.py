import psycopg

from ..config import settings
from .embed import embed_texts


def retrieve_top_k(question: str, top_k: int = 5) -> list[str]:
    embedding = embed_texts([question])[0]
    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
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
