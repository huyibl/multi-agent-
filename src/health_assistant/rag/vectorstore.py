"""Chroma 向量库管理。"""

from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config.settings import Settings, get_settings
from health_assistant.rag.embedder import create_embedder


def get_vectorstore(
    settings: Optional[Settings] = None,
    embedder: Optional[Embeddings] = None,
) -> Chroma:
    """获取或创建持久化 Chroma 向量库。"""
    settings = settings or get_settings()
    embedder = embedder or create_embedder(settings)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embedder,
        persist_directory=str(settings.chroma_persist_dir),
    )


def add_documents(
    documents: list[Document],
    settings: Optional[Settings] = None,
) -> int:
    """向向量库添加文档，返回入库数量。"""
    if not documents:
        return 0
    store = get_vectorstore(settings)
    store.add_documents(documents)
    return len(documents)


def similarity_search(
    query: str,
    k: int = 5,
    doc_types: list[str] | None = None,
    settings: Optional[Settings] = None,
) -> list[Document]:
    """在向量库中检索，可选 metadata 过滤。"""
    settings = settings or get_settings()
    store = get_vectorstore(settings)
    if doc_types:
        # Chroma 过滤：匹配任意 doc_type
        filter_dict = {"doc_type": {"$in": doc_types}}
        return store.similarity_search(query, k=k, filter=filter_dict)
    return store.similarity_search(query, k=k)
