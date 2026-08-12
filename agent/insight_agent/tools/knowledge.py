from ..rag.retriever import retrieve_top_k


def query_knowledge_base(question: str, top_k: int = 5) -> str:
    chunks = retrieve_top_k(question, top_k)
    if not chunks:
        return "知识库中未检索到相关内容"
    return "\n---\n".join(chunks)
