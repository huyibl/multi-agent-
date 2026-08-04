"""RAG 管道集成测试。"""

from pathlib import Path

from config.settings import get_settings
from health_assistant.rag.chunkers import chunk_documents
from health_assistant.rag.loaders import load_directory


def test_load_sample_documents():
    settings = get_settings()
    docs = load_directory(settings.data_raw_dir)
    assert len(docs) >= 2


def test_chunk_sample_documents():
    settings = get_settings()
    docs = load_directory(settings.data_raw_dir)
    chunks = chunk_documents(docs)
    assert len(chunks) >= len(docs)
