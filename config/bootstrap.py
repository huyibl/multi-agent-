"""启动引导：将 Streamlit Secrets 注入环境变量，供 Settings 读取。"""

from __future__ import annotations

import os
from pathlib import Path

SECRET_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "DASHSCOPE_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_DIMENSION",
    "CHROMA_PERSIST_DIR",
    "CHROMA_COLLECTION_NAME",
    "PLANNER_USE_LLM",
    "REVIEWER_USE_LLM",
    "RETRIEVAL_MERGE_QUERIES",
    "MAX_REVIEW_RETRIES",
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "ANONYMIZED_TELEMETRY",
)


def _secrets_file_exists() -> bool:
    """本地是否存在 secrets.toml（避免无文件时触发 Streamlit 异常）。"""
    candidates = [
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml",
        Path(__file__).resolve().parent.parent / "app" / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    return any(p.is_file() for p in candidates)


def apply_streamlit_secrets() -> bool:
    """若运行在 Streamlit 且存在 secrets，写入 os.environ（不覆盖已有环境变量）。"""
    try:
        import streamlit as st
    except ImportError:
        return False

    # 本地无 secrets.toml 且非 Cloud 时直接跳过，避免 StreamlitSecretNotFoundError
    if not is_streamlit_cloud() and not _secrets_file_exists():
        return False

    try:
        secrets = st.secrets
        # 触发解析；无文件时会抛 StreamlitSecretNotFoundError
        _ = list(secrets.keys()) if hasattr(secrets, "keys") else len(secrets)
    except Exception:
        return False

    applied = False
    for key in SECRET_ENV_KEYS:
        if key in os.environ and os.environ[key]:
            continue
        try:
            value = secrets.get(key) if hasattr(secrets, "get") else secrets[key]
        except Exception:
            continue
        if value is None or value == "":
            continue
        os.environ[key] = str(value)
        applied = True

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    return applied


def has_streamlit_secrets() -> bool:
    """安全检测是否存在可用的 Streamlit secrets。"""
    if not is_streamlit_cloud() and not _secrets_file_exists():
        return False
    try:
        import streamlit as st

        return len(list(st.secrets.keys())) > 0
    except Exception:
        return False


def is_streamlit_cloud() -> bool:
    """检测是否运行在 Streamlit Community Cloud。"""
    if os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"):
        return True
    cwd = os.getcwd().replace("\\", "/")
    if cwd.startswith("/mount/src"):
        return True
    return False
