"""健康知识库文档加载器。"""

from pathlib import Path
from typing import Iterator

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document


def infer_doc_type(path: Path) -> str:
    """根据父目录名推断文档类型。"""
    parent = path.parent.name.lower()
    mapping = {
        "dietary_guidelines": "dietary_guideline",
        "exercise_literature": "exercise",
        "nutrition_tables": "nutrition_table",
    }
    return mapping.get(parent, "general")


def load_document(path: Path) -> list[Document]:
    """根据文件扩展名加载单个文档。"""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        docs = PyPDFLoader(str(path)).load()
    elif suffix == ".csv":
        docs = CSVLoader(str(path), encoding="utf-8").load()
    elif suffix in (".md", ".txt"):
        docs = TextLoader(str(path), encoding="utf-8").load()
    else:
        return []

    doc_type = infer_doc_type(path)
    for i, doc in enumerate(docs):
        doc.metadata.setdefault("source", path.name)
        doc.metadata.setdefault("doc_type", doc_type)
        doc.metadata.setdefault("file_path", str(path))
        if "page" not in doc.metadata:
            doc.metadata["page"] = i + 1
    return docs


def load_directory(raw_dir: Path) -> list[Document]:
    """从原始数据目录加载所有支持的文档。"""
    documents: list[Document] = []
    patterns = ["**/*.pdf", "**/*.md", "**/*.txt", "**/*.csv"]
    for pattern in patterns:
        for path in raw_dir.glob(pattern):
            try:
                documents.extend(load_document(path))
            except Exception:
                continue
    return documents


def iter_source_files(raw_dir: Path) -> Iterator[Path]:
    """遍历所有可入库的源文件。"""
    for pattern in ["**/*.pdf", "**/*.md", "**/*.txt", "**/*.csv"]:
        yield from raw_dir.glob(pattern)
