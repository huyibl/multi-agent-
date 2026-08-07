"""Chroma 向量库管理。"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config.settings import Settings, get_settings
from config.sqlite_patch import apply_sqlite_patch
from health_assistant.rag.embedder import create_embedder

logger = logging.getLogger(__name__)

# 进程内复用同一个 client，避免重复打开损坏连接
_CLIENT: Any = None
_CLIENT_PATH: str | None = None


def reset_client_cache() -> None:
    """清空进程内 Chroma client 缓存（重建向量库前调用）。"""
    global _CLIENT, _CLIENT_PATH
    _CLIENT = None
    _CLIENT_PATH = None


def _make_persistent_client(persist_dir: str):
    """创建本地 PersistentClient。

    注意：不要传入自定义 Settings 覆盖 ``is_persistent``，
    否则 Cloud 上可能误连 HTTP 服务并报 default_tenant。
    """
    apply_sqlite_patch()
    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    # 仅传 path，让 chromadb 自行设置 is_persistent / persist_directory
    return chromadb.PersistentClient(path=str(path))


def get_chroma_client(persist_dir: str, *, force_new: bool = False):
    """获取（或重建）Chroma PersistentClient。"""
    global _CLIENT, _CLIENT_PATH
    apply_sqlite_patch()

    if (
        not force_new
        and _CLIENT is not None
        and _CLIENT_PATH == persist_dir
    ):
        return _CLIENT

    try:
        client = _make_persistent_client(persist_dir)
    except Exception as first_err:
        logger.warning("Chroma open failed (%s); wiping %s", first_err, persist_dir)
        shutil.rmtree(persist_dir, ignore_errors=True)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        try:
            client = _make_persistent_client(persist_dir)
        except Exception as second_err:
            raise RuntimeError(
                "无法初始化 Chroma 向量库。"
                f" 首次错误: {first_err}; 清空后仍失败: {second_err}."
                " 请确认已安装 pysqlite3-binary，且 Cloud 使用 Python 3.11。"
            ) from second_err

    _CLIENT = client
    _CLIENT_PATH = persist_dir
    return client


def get_vectorstore(
    settings: Optional[Settings] = None,
    embedder: Optional[Embeddings] = None,
) -> Chroma:
    """获取或创建持久化 Chroma 向量库。"""
    settings = settings or get_settings()
    embedder = embedder or create_embedder(settings)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

    client = get_chroma_client(str(settings.chroma_persist_dir))
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
    persist = str(settings.chroma_persist_dir)

    # 重建：清缓存 + 删 collection；失败则整库清空再写
    reset_client_cache()
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
