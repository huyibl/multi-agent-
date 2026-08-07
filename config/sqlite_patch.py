"""Streamlit Cloud 上用 pysqlite3 替换系统 sqlite3，供 Chroma 使用。"""

from __future__ import annotations

import sys


def apply_sqlite_patch() -> bool:
    """若已安装 pysqlite3，则替换 ``sys.modules['sqlite3']``。

    Returns:
        是否成功完成替换。
    """
    try:
        import pysqlite3  # type: ignore

        # 官方推荐：pop 后再挂到 sqlite3，避免残留旧模块
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
        return True
    except ImportError:
        return False


def sqlite_info() -> dict:
    """返回当前生效的 sqlite 模块信息（便于 Cloud 排障）。"""
    import sqlite3

    return {
        "patched": "pysqlite3" in type(sqlite3).__module__ or sqlite3.__name__ == "pysqlite3",
        "module": getattr(sqlite3, "__name__", str(sqlite3)),
        "sqlite_version": getattr(sqlite3, "sqlite_version", "unknown"),
    }
