"""启动引导：Secrets 注入、Cloud 路径与 SQLite 补丁。"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLOUD_CHROMA_DIR = Path("/tmp/chroma_health")

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

_SECRETS_APPLIED = False


def _apply_sqlite_patch() -> bool:
    """延迟导入，避免 ``config`` 包名冲突时启动失败。"""
    try:
        from health_assistant.utils.sqlite_patch import apply_sqlite_patch

        return apply_sqlite_patch()
    except Exception:
        try:
            import pysqlite3  # type: ignore
            import sys

            sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
            return True
        except Exception:
            return False


def _has_script_run_ctx() -> bool:
    """仅在主脚本线程且 Session 已初始化时才允许访问 ``st.secrets``。"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


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
    """若运行在 Streamlit 且存在 secrets，写入 os.environ（不覆盖已有环境变量）。

    无 ScriptRunContext（例如 ThreadPool 工作线程）时直接跳过，
    避免 ``Tried to use SessionInfo before it was initialized``。
    """
    global _SECRETS_APPLIED
    if _SECRETS_APPLIED:
        return True

    # 本地无 secrets.toml 且非 Cloud 时直接跳过
    if not is_streamlit_cloud() and not _secrets_file_exists():
        return False

    # 后台线程 / 导入阶段：禁止碰 st.secrets
    if not _has_script_run_ctx():
        return False

    try:
        import streamlit as st

        secrets = st.secrets
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
    _SECRETS_APPLIED = True
    return applied


def has_streamlit_secrets() -> bool:
    """安全检测是否存在可用的 Streamlit secrets。"""
    if not is_streamlit_cloud() and not _secrets_file_exists():
        return False
    if not _has_script_run_ctx():
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


def configure_cloud_chroma():
    """Cloud 上将向量库落到可写的 ``/tmp``。"""
    _apply_sqlite_patch()
    if not is_streamlit_cloud():
        return None

    if os.environ.get("CHROMA_PERSIST_DIR"):
        path = Path(os.environ["CHROMA_PERSIST_DIR"])
        path.mkdir(parents=True, exist_ok=True)
        return path

    dest = CLOUD_CHROMA_DIR
    dest.mkdir(parents=True, exist_ok=True)
    os.environ["CHROMA_PERSIST_DIR"] = str(dest)
    return dest


def prepare_runtime() -> None:
    """应用启动时调用：SQLite 补丁 + Cloud Chroma 路径。"""
    _apply_sqlite_patch()
    configure_cloud_chroma()
