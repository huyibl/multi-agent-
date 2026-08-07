"""多 Agent 体系的抽象基类与公共依赖注入。"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from config.settings import Settings, get_settings
from health_assistant.utils.llm_factory import create_llm, load_prompt


class BaseAgent(ABC):
    """所有健身教练 Agent 的抽象基类。

    子类通过 ``prompt_name`` 绑定 YAML Prompt，并实现 ``run``。
    """

    prompt_name: str = ""

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        settings: Optional[Settings] = None,
    ):
        """初始化 Settings 与 LLM（可注入以便测试）。"""
        self.settings = settings or get_settings()
        self.llm = llm or create_llm(self.settings)

    @property
    def prompt(self) -> dict[str, str]:
        """加载当前 Agent 的 system / user 模板。"""
        return load_prompt(self.prompt_name, self.settings)

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """执行 Agent 主逻辑，返回结构化输出。"""