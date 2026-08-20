"""混合检索：关键词（中文二元组 + 命中计数排序）与向量（bge-m3 + pgvector）双路召回，RRF 融合。

返回带来源标注的片段：[score=0.0432|文档:data-dictionary] 内容...
embedding 不可用时自动退化为关键词检索（同样带相关度排序与来源）。
"""

import re

import psycopg

from ..config import settings
from .embed import embed_texts

RRF_K = 60


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


def _rank_by_terms(candidates: list[tuple[int, str, str]], terms: list[str]) -> list[int]:
    """关键词候选按命中的二元组数量降序排序，返回 id 列表（相关性高的在前）。"""
    scored = []
    for cid, _title, content in candidates:
        text = content.lower()
        hits = sum(1 for term in terms if term.lower() in text)
        if hits > 0:
            scored.append((cid, hits))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return [cid for cid, _ in scored]


def _rrf_merge(term_ids: list[int], vector_ids: list[int], top_k: int) -> dict[int, float]:
    """Reciprocal Rank Fusion：两路排序结果按 rank 加权求和，返回取 top_k 的 {id: score}。"""
    scores: dict[int, float] = {}
    for rank, cid in enumerate(term_ids):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, cid in enumerate(vector_ids):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    ranked = sorted(scores.items(), key=lambda item: -item[1])
    return dict(ranked[:top_k])


def retrieve_top_k(question: str, top_k: int = 5) -> list[str]:
    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.document_chunks')")
            table_exists = cur.fetchone()[0] is not None
    if not table_exists:
        return []

    embedding = None
    if settings.embedding_enabled:
        try:
            embedding = embed_texts([question])[0]
        except Exception:  # noqa: BLE001
            embedding = None

    terms = _keyword_terms(question)
    patterns = [f"%{term}%" for term in terms]

    with psycopg.connect(settings.postgres_dsn, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    SELECT id, document_title, content
                    FROM document_chunks
                    WHERE content ILIKE ANY(%s)
                    ORDER BY id
                    LIMIT 50
                    """,
                    (patterns,),
                )
                term_candidates = cur.fetchall()
            except Exception:  # noqa: BLE001
                term_candidates = []

            vector_candidates = []
            if embedding is not None:
                try:
                    cur.execute(
                        """
                        SELECT id, document_title, content
                        FROM document_chunks
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT 50
                        """,
                        (str(embedding),),
                    )
                    vector_candidates = cur.fetchall()
                except Exception:  # noqa: BLE001
                    vector_candidates = []

    term_ranked = _rank_by_terms(term_candidates, terms)
    vector_ranked = [cid for cid, _title, _content in vector_candidates]
    id_to_chunk = {cid: (title, content) for cid, title, content in term_candidates + vector_candidates}

    if embedding is not None and vector_ranked:
        merged = _rrf_merge(term_ranked, vector_ranked, top_k)
        results = []
        for cid, score in merged.items():
            title, content = id_to_chunk.get(cid, ("unknown", ""))
            results.append(f"[score={score:.4f}|文档:{title}] {content}")
        return results

    # 纯关键词模式（无 embedding 或向量结果）
    results = []
    for cid in term_ranked[:top_k]:
        title, content = id_to_chunk.get(cid, ("unknown", ""))
        results.append(f"[score=0|文档:{title}] {content}")
    return results
