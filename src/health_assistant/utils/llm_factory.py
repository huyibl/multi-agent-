"""OpenAI 兼容 LLM 客户端工厂。"""

import json
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.settings import Settings, get_settings


def create_llm(settings: Optional[Settings] = None) -> ChatOpenAI:
    """创建指向 DeepSeek 或兼容 API 的 ChatOpenAI 实例。"""
    settings = settings or get_settings()
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key or "not-set",
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )


def load_prompt(name: str, settings: Optional[Settings] = None) -> dict[str, str]:
    """按 Agent 名称加载 YAML Prompt 模板。"""
    import yaml

    settings = settings or get_settings()
    path = settings.prompts_dir / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def invoke_llm_json(
    llm: ChatOpenAI,
    system: str,
    user: str,
    fallback: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """调用 LLM 并解析 JSON 响应。"""
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    response = llm.invoke(messages)
    text = response.content if isinstance(response.content, str) else str(response.content)
    parsed = extract_json(text)
    if parsed is not None:
        return parsed
    return fallback or {}


def extract_json(text: str) -> Optional[dict[str, Any]]:
    """从 LLM 响应文本中提取 JSON 对象。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None
