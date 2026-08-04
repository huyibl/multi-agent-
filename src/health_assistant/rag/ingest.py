"""知识库入库管道。"""

import logging
from typing import Optional

from config.settings import Settings, get_settings
from health_assistant.rag.chunkers import chunk_documents
from health_assistant.rag.loaders import load_directory
from health_assistant.rag.vectorstore import add_documents

logger = logging.getLogger(__name__)


def ingest_knowledge_base(settings: Optional[Settings] = None) -> dict:
    """加载、切块、嵌入并存储所有原始文档。"""
    settings = settings or get_settings()
    raw_dir = settings.data_raw_dir

    logger.info("Loading documents from %s", raw_dir)
    documents = load_directory(raw_dir)
    if not documents:
        logger.warning("No documents found in %s", raw_dir)
        return {"loaded": 0, "chunks": 0, "stored": 0}

    logger.info("Loaded %d document pages", len(documents))
    chunks = chunk_documents(documents, settings)
    logger.info("Created %d chunks", len(chunks))

    stored = add_documents(chunks, settings)
    logger.info("Stored %d chunks in Chroma", stored)
    return {"loaded": len(documents), "chunks": len(chunks), "stored": stored}
