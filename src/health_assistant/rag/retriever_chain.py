"""带 metadata 过滤的检索链。"""

from typing import Optional

from config.settings import Settings, get_settings
from health_assistant.rag.vectorstore import similarity_search
from health_assistant.schemas.agent_io import RetrievedChunk


class HealthRetriever:
    """健康知识库的高层检索器。"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def retrieve(
        self,
        queries: list[str],
        doc_types: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """对查询检索并去重；默认合并为单次 embedding 调用。"""
        top_k = top_k or self.settings.retrieval_top_k

        if self.settings.retrieval_merge_queries and queries:
            search_query = queries[0]
        else:
            search_query = queries[0] if len(queries) == 1 else " ".join(queries[:3])

        docs = similarity_search(
            query=search_query,
            k=top_k,
            doc_types=doc_types,
            settings=self.settings,
        )

        chunks: list[RetrievedChunk] = []
        seen: set[str] = set()
        for doc in docs:
            key = doc.page_content[:100]
            if key in seen:
                continue
            seen.add(key)
            meta = doc.metadata or {}
            chunks.append(
                RetrievedChunk(
                    content=doc.page_content,
                    source=meta.get("source", meta.get("file_path", "unknown")),
                    page=meta.get("page"),
                    doc_type=meta.get("doc_type", ""),
                    score=meta.get("score", 0.0),
                )
            )
        return chunks[:top_k]
