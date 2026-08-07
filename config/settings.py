"""AI 健身教练应用配置：从环境变量 / ``.env`` / Streamlit Secrets 加载。"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """AI 健身教练的中央配置。"""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 大语言模型
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")

    # 文本嵌入
    dashscope_api_key: str = Field(default="", alias="DASHSCOPE_API_KEY")
    embedding_model: str = Field(default="text-embedding-v4", alias="EMBEDDING_MODEL")
    embedding_provider: Literal["dashscope", "local"] = Field(
        default="dashscope", alias="EMBEDDING_PROVIDER"
    )
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    local_embedding_model: str = Field(default="BAAI/bge-m3", alias="LOCAL_EMBEDDING_MODEL")

    # 向量数据库
    chroma_persist_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "chroma", alias="CHROMA_PERSIST_DIR"
    )
    chroma_collection_name: str = Field(
        default="health_knowledge", alias="CHROMA_COLLECTION_NAME"
    )

    # 检索增强生成（RAG）参数
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=64, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")

    # 数据路径
    data_raw_dir: Path = Field(default=PROJECT_ROOT / "data" / "raw")
    data_processed_dir: Path = Field(default=PROJECT_ROOT / "data" / "processed")
    prompts_dir: Path = Field(default=PROJECT_ROOT / "config" / "prompts")

    # LangSmith 可观测性
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="health-assistant", alias="LANGCHAIN_PROJECT")

    # 应用配置
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_review_retries: int = Field(default=2, alias="MAX_REVIEW_RETRIES")
    planner_use_llm: Literal["auto", "always", "never"] = Field(
        default="auto", alias="PLANNER_USE_LLM"
    )
    reviewer_use_llm: Literal["auto", "always", "never"] = Field(
        default="auto", alias="REVIEWER_USE_LLM"
    )
    retrieval_merge_queries: bool = Field(default=True, alias="RETRIEVAL_MERGE_QUERIES")

    def configure_tracing(self) -> None:
        """配置完成后启用 LangSmith 追踪。"""
        import os

        if self.langchain_tracing_v2 and self.langchain_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project


@lru_cache
def get_settings() -> Settings:
    """返回缓存的配置实例。"""
    try:
        from config.bootstrap import apply_streamlit_secrets, prepare_runtime
        from config.sqlite_patch import apply_sqlite_patch

        apply_sqlite_patch()
        apply_streamlit_secrets()
        prepare_runtime()
    except Exception:
        pass
    return Settings()


def clear_settings_cache() -> None:
    """测试或 Secrets 变更后清除缓存。"""
    get_settings.cache_clear()
