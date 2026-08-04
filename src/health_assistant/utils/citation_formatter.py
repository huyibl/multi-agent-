"""RAG 引用来源格式化。"""

from health_assistant.schemas.agent_io import RetrievedChunk


def format_citations(chunks: list[RetrievedChunk]) -> list[str]:
    """从检索块生成带编号的引用字符串。"""
    citations = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.source or "未知来源"
        page = f", 第{chunk.page}页" if chunk.page else ""
        preview = chunk.content[:120].replace("\n", " ")
        citations.append(f"[{i}] {source}{page}: {preview}...")
    return citations


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    """格式化检索块，用于写入 Agent Prompt。"""
    if not chunks:
        return "（无检索结果）"
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta = f"[{i}] {chunk.source}"
        if chunk.doc_type:
            meta += f" ({chunk.doc_type})"
        parts.append(f"{meta}\n{chunk.content}")
    return "\n\n".join(parts)
