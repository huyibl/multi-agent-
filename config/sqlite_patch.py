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

        sys.modules["sqlite3"] = pysqlite3
        return True
    except ImportError:
        return False
