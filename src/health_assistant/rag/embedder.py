"""嵌入模型：DashScope API 与本地 bge-m3。"""

from typing import Optional

from langchain_core.embeddings import Embeddings

from config.settings import Settings, get_settings


class DashScopeEmbeddings(Embeddings):
    """DashScope text-embedding-v4 封装。"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v4",
        dimension: int = 1024,
    ):
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import dashscope
        from dashscope import TextEmbedding

        dashscope.api_key = self.api_key
        embeddings: list[list[float]] = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = TextEmbedding.call(
                model=self.model,
                input=batch,
                dimension=self.dimension,
                text_type="document",
            )
            if resp.status_code != 200:
                raise RuntimeError(f"DashScope embedding failed: {resp.message}")
            for item in resp.output["embeddings"]:
                embeddings.append(item["embedding"])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        import dashscope
        from dashscope import TextEmbedding

        dashscope.api_key = self.api_key
        resp = TextEmbedding.call(
            model=self.model,
            input=text,
            dimension=self.dimension,
            text_type="query",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"DashScope embedding failed: {resp.message}")
        return resp.output["embeddings"][0]["embedding"]


class LocalEmbeddings(Embeddings):
    """本地 sentence-transformers 嵌入（bge-m3）。"""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()


def create_embedder(settings: Optional[Settings] = None) -> Embeddings:
    """根据配置创建嵌入模型。"""
    settings = settings or get_settings()
    if settings.embedding_provider == "dashscope" and settings.dashscope_api_key:
        return DashScopeEmbeddings(
            api_key=settings.dashscope_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
    return LocalEmbeddings(model_name=settings.local_embedding_model)
