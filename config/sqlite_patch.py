"""兼容旧导入路径；实现见 ``health_assistant.utils.sqlite_patch``。"""

from health_assistant.utils.sqlite_patch import apply_sqlite_patch, sqlite_info

__all__ = ["apply_sqlite_patch", "sqlite_info"]
