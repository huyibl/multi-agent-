"""Agent 基础工具类。"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from config.settings import Settings, get_settings
from health_assistant.utils.llm_factory import create_llm, load_prompt


class BaseAgent(ABC):
    """所有 Agent 的抽象基类。"""

    prompt_name: str = ""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.llm = llm or create_llm(self.settings)

    @property
    def prompt(self) -> dict[str, str]:
        return load_prompt(self.prompt_name, self.settings)

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """执行 Agent 逻辑。"""
