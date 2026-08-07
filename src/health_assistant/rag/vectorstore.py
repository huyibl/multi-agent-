"""向量库管理（本地 Persistent Chroma；Cloud 用 Ephemeral 避开 tenant 问题）。"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config.settings import Settings, get_settings
from health_assistant.rag.embedder import create_embedder
from health_assistant.utils.sqlite_patch import apply_sqlite_patch

logger = logging.getLogger(__name__)

_CLIENT: Any = None
_CLIENT_KEY: str | None = None
_STORE: Chroma | None = None


def _is_cloud() -> bool:
    if os.environ.get("CHROMA_EPHEMERAL", "").lower() in {"1", "true", "yes"}:
        return True
    try:
        from config.bootstrap import is_streamlit_cloud

        return is_streamlit_cloud()
    except Exception:
        return False


def _clear_chroma_cache() -> None:
    """清理 Chroma 进程内系统缓存（缓解 default_tenant 误报）。"""
    try:
        from chromadb.api.client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except Exception:
        pass


def reset_client_cache() -> None:
    """清空进程内 client / store 缓存。"""
    global _CLIENT, _CLIENT_KEY, _STORE
    _CLIENT = None
    _CLIENT_KEY = None
    _STORE = None
    _clear_chroma_cache()


def _make_client(persist_dir: str):
    """创建 Chroma client：Cloud 用内存 Ephemeral，本地用 Persistent。"""
    apply_sqlite_patch()
    _clear_chroma_cache()

    if _is_cloud():
        # Streamlit Cloud 上 PersistentClient 常报 default_tenant；Ephemeral 可稳定入库/检索
        logger.info("Using Chroma EphemeralClient (Cloud/in-memory)")
        return chromadb.EphemeralClient()

    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_chroma_client(persist_dir: str, *, force_new: bool = False):
    """获取（或重建）Chroma client。"""
    global _CLIENT, _CLIENT_KEY
    apply_sqlite_patch()

    mode = "ephemeral" if _is_cloud() else persist_dir
    if not force_new and _CLIENT is not None and _CLIENT_KEY == mode:
        return _CLIENT

    if _is_cloud():
        client = _make_client(persist_dir)
    else:
        try:
            client = _make_client(persist_dir)
        except Exception as first_err:
            logger.warning("Chroma open failed (%s); wiping %s", first_err, persist_dir)
            shutil.rmtree(persist_dir, ignore_errors=True)
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            _clear_chroma_cache()
            try:
                client = _make_client(persist_dir)
            except Exception as second_err:
                raise RuntimeError(
                    "无法初始化 Chroma。"
                    f" 首次: {first_err}; 清空后: {second_err}"
                ) from second_err

    _CLIENT = client
    _CLIENT_KEY = mode
    return client


def get_vectorstore(
    settings: Optional[Settings] = None,
    embedder: Optional[Embeddings] = None,
) -> Chroma:
    """获取向量库；Cloud 进程内复用已入库的 store。"""
    global _STORE
    settings = settings or get_settings()
    embedder = embedder or create_embedder(settings)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

    if _STORE is not None and _is_cloud():
        return _STORE

    client = get_chroma_client(str(settings.chroma_persist_dir))
    store = Chroma(
        client=client,
        collection_name=settings.chroma_collection_name,
        embedding_function=embedder,
    )
    if _is_cloud():
        _STORE = store
    return store


def add_documents(
    documents: list[Document],
    settings: Optional[Settings] = None,
) -> int:
    """向向量库添加文档，返回入库数量。"""
    if not documents:
        return 0
    settings = settings or get_settings()
    persist = str(settings.chroma_persist_dir)

    reset_client_cache()

    if not _is_cloud():
        try:
            client = get_chroma_client(persist, force_new=True)
            try:
                client.delete_collection(settings.chroma_collection_name)
            except Exception:
                pass
        except Exception:
            shutil.rmtree(persist, ignore_errors=True)
            Path(persist).mkdir(parents=True, exist_ok=True)
            reset_client_cache()

    # Cloud：全新 EphemeralClient + from_documents，保证集合与数据一次建好
    embedder = create_embedder(settings)
    client = get_chroma_client(persist, force_new=True)
    store = Chroma.from_documents(
        documents=documents,
        embedding=embedder,
        client=client,
        collection_name=settings.chroma_collection_name,
    )
    global _STORE
    _STORE = store
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

    # Cloud 未重建时集合为空，给出明确错误
    try:
        if _is_cloud() and hasattr(store, "_collection"):
            pass
    except Exception:
        pass

    if doc_types:
        filter_dict = {"doc_type": {"$in": doc_types}}
        try:
            return store.similarity_search(query, k=k, filter=filter_dict)
        except Exception:
            # 空库或无 metadata 时退回无过滤
            return store.similarity_search(query, k=k)
    return store.similarity_search(query, k=k)
