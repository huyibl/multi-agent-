"""知识库入库服务。"""

from typing import Optional

from config.settings import Settings, get_settings
from health_assistant.rag.ingest import ingest_knowledge_base


class IngestService:
    """知识库入库流程的服务封装。"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def run(self) -> dict:
        """执行完整入库管道。"""
        return ingest_knowledge_base(self.settings)
