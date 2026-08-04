"""文本切块单元测试。"""

from langchain_core.documents import Document

from health_assistant.rag.chunkers import chunk_documents


def test_chunk_documents():
    docs = [
        Document(page_content="A" * 600, metadata={"source": "test.md"}),
    ]
    chunks = chunk_documents(docs)
    assert len(chunks) >= 1
    assert all(c.metadata.get("source") == "test.md" for c in chunks)
