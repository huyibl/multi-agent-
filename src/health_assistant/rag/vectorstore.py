"""Chroma 向量库管理。"""

from __future__ import annotations

import logging
import shutil
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaClientSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config.settings import Settings, get_settings
from health_assistant.rag.embedder import create_embedder

logger = logging.getLogger(__name__)


def _chroma_settings() -> ChromaClientSettings:
    return ChromaClientSettings(anonymized_telemetry=False, allow_reset=True)


def _persistent_client(persist_dir: str) -> chromadb.PersistentClient:
    """创建 PersistentClient；若租户元数据损坏则清空目录后重建。"""
    try:
        return chromadb.PersistentClient(path=persist_dir, settings=_chroma_settings())
    except ValueError as exc:
        # Cloud / 跨平台常见：Could not connect to tenant default_tenant
        logger.warning("Chroma open failed (%s); resetting %s", exc, persist_dir)
        path = __import__("pathlib").Path(persist_dir)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=persist_dir, settings=_chroma_settings())


def get_vectorstore(
    settings: Optional[Settings] = None,
    embedder: Optional[Embeddings] = None,
) -> Chroma:
    """获取或创建持久化 Chroma 向量库。"""
    settings = settings or get_settings()
    embedder = embedder or create_embedder(settings)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

    client = _persistent_client(str(settings.chroma_persist_dir))
    return Chroma(
        client=client,
        collection_name=settings.chroma_collection_name,
        embedding_function=embedder,
    )


def add_documents(
    documents: list[Document],
    settings: Optional[Settings] = None,
) -> int:
    """向向量库添加文档，返回入库数量。"""
    if not documents:
        return 0
    settings = settings or get_settings()
    # 重建前清空同名 collection，避免重复写入
    try:
        client = _persistent_client(str(settings.chroma_persist_dir))
        client.delete_collection(settings.chroma_collection_name)
    except Exception:
        pass

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
        filter_dict = {"doc_type": {"$in": doc_types}}
        return store.similarity_search(query, k=k, filter=filter_dict)
    return store.similarity_search(query, k=k)
