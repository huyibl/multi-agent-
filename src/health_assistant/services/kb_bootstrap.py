"""知识库自动就绪：Cloud 冷启动时无需手动「重建向量库」。"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from config.settings import Settings, get_settings
from health_assistant.rag.ingest import ingest_knowledge_base
from health_assistant.rag import vectorstore as vs

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_LAST_STATUS: dict[str, Any] = {
    "ready": False,
    "stored": 0,
    "source": "none",
    "error": None,
}


def kb_status() -> dict[str, Any]:
    """返回最近一次确保知识库就绪的状态快照。"""
    return dict(_LAST_STATUS)


def _collection_count(settings: Settings) -> int:
    """当前进程内向量库文档数；不可用则返回 0。"""
    try:
        store = vs.get_vectorstore(settings)
        col = getattr(store, "_collection", None)
        if col is not None and hasattr(col, "count"):
            return int(col.count())
        # 兜底：试检索
        docs = store.similarity_search("protein", k=1)
        return 1 if docs else 0
    except Exception as exc:
        logger.info("kb count probe failed: %s", exc)
        return 0


def ensure_kb_ready(
    settings: Optional[Settings] = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """确保向量库可用；Cloud 空库时自动从 ``data/raw`` 入库。

    Args:
        settings: 可选配置。
        force: True 时强制重新入库（管理员重建）。

    Returns:
        状态字典：ready / stored / source / error。
    """
    global _LAST_STATUS
    settings = settings or get_settings()

    with _LOCK:
        if not force:
            n = _collection_count(settings)
            if n > 0:
                _LAST_STATUS = {
                    "ready": True,
                    "stored": n,
                    "source": "memory",
                    "error": None,
                }
                return dict(_LAST_STATUS)

        try:
            logger.info("Auto-ingest knowledge base (force=%s)…", force)
            if force:
                vs.reset_client_cache()
            result = ingest_knowledge_base(settings)
            stored = int(result.get("stored") or 0)
            _LAST_STATUS = {
                "ready": stored > 0,
                "stored": stored,
                "source": "auto_ingest",
                "error": None if stored > 0 else "入库结果为 0，请检查 data/raw 与 Embedding Key",
                "loaded": result.get("loaded", 0),
                "chunks": result.get("chunks", 0),
            }
        except Exception as exc:
            logger.exception("auto-ingest failed: %s", exc)
            _LAST_STATUS = {
                "ready": False,
                "stored": 0,
                "source": "auto_ingest",
                "error": str(exc),
            }
        return dict(_LAST_STATUS)
