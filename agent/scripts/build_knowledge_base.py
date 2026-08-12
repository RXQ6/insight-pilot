import os
from pathlib import Path

import psycopg

from insight_agent.config import settings
from insight_agent.rag.chunker import split_markdown
from insight_agent.rag.embed import embed_texts


def main() -> None:
    docs_dir = Path(os.getenv("KNOWLEDGE_DIR", "docs"))
    if not docs_dir.exists():
        print("docs directory not found, skip knowledge base build")
        return

    documents = []
    for path in sorted(docs_dir.rglob("*.md")):
        documents.append((path.stem, str(path), path.read_text(encoding="utf-8")))
    if not documents:
        print("no markdown documents found")
        return

    chunks = []
    for title, source, content in documents:
        for index, chunk in enumerate(split_markdown(content)):
            chunks.append((title, source, index, chunk))

    vectors = embed_texts([chunk[3] for chunk in chunks])

    with psycopg.connect(settings.postgres_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    document_title VARCHAR(255),
                    source TEXT,
                    chunk_index INT,
                    content TEXT,
                    embedding vector(1024)
                )
                """
            )
            cur.execute("TRUNCATE document_chunks")
            for (title, source, index, content), vector in zip(chunks, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO document_chunks (document_title, source, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    """,
                    (title, source, index, content, str(vector)),
                )
    print(f"knowledge base built: {len(chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    main()
