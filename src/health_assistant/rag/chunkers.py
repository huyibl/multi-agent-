"""RAG 文本切块策略。"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import Settings, get_settings


def create_splitter(settings: Settings | None = None) -> RecursiveCharacterTextSplitter:
    """创建配置好的文本分割器。"""
    settings = settings or get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )


def chunk_documents(
    documents: list[Document],
    settings: Settings | None = None,
) -> list[Document]:
    """将文档切分为块，并保留元数据。"""
    splitter = create_splitter(settings)
    return splitter.split_documents(documents)
