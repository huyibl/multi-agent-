"""Cloud Demo 用量限额：防刷 API。

策略（默认仅 Streamlit Cloud 启用）：
- 会话限额：同一浏览器 session 最多 N 次
- 全站日限额：进程/实例当日最多 M 次（/tmp 计数文件）
- 冷却：两次请求至少间隔 C 秒

可通过 Secrets / 环境变量覆盖：
DEMO_RATE_LIMIT=1|0
DEMO_SESSION_LIMIT=10
DEMO_DAILY_LIMIT=80
DEMO_COOLDOWN_SEC=20
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_LOCK = threading.Lock()


@dataclass
class RateLimitConfig:
    enabled: bool
    session_limit: int
    daily_limit: int
    cooldown_sec: float
    counter_path: Path


@dataclass
class RateLimitResult:
    allowed: bool
    reason: str = ""
    session_used: int = 0
    session_limit: int = 0
    daily_used: int = 0
    daily_limit: int = 0
    retry_after_sec: float = 0.0


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def _is_cloud() -> bool:
    if os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"):
        return True
    cwd = os.getcwd().replace("\\", "/")
    if cwd.startswith("/mount/src"):
        return True
    try:
        from config.bootstrap import is_streamlit_cloud

        return is_streamlit_cloud()
    except Exception:
        return False


def load_config(app_name: str = "demo") -> RateLimitConfig:
    flag = os.environ.get("DEMO_RATE_LIMIT", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        enabled = True
    elif flag in {"0", "false", "no", "off"}:
        enabled = False
    else:
        enabled = _is_cloud()

    return RateLimitConfig(
        enabled=enabled,
        session_limit=_env_int("DEMO_SESSION_LIMIT", 10),
        daily_limit=_env_int("DEMO_DAILY_LIMIT", 100),
        cooldown_sec=_env_float("DEMO_COOLDOWN_SEC", 15.0),
        counter_path=Path(f"/tmp/{app_name}_demo_quota.json")
        if _is_cloud()
        else Path(os.environ.get("TEMP", ".")) / f"{app_name}_demo_quota.json",
    )


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def _read_daily(path: Path) -> dict:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("date") == _today():
                return data
    except Exception:
        pass
    return {"date": _today(), "count": 0}


def _write_daily(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def check_rate_limit(
    *,
    app_name: str,
    session_state: dict,
    config: Optional[RateLimitConfig] = None,
) -> RateLimitResult:
    cfg = config or load_config(app_name)
    session_used = int(session_state.get("_demo_session_used", 0) or 0)
    last_ts = float(session_state.get("_demo_last_ts", 0) or 0)

    if not cfg.enabled:
        return RateLimitResult(
            allowed=True,
            session_used=session_used,
            session_limit=cfg.session_limit,
            daily_used=0,
            daily_limit=cfg.daily_limit,
        )

    with _LOCK:
        daily = _read_daily(cfg.counter_path)
        daily_used = int(daily.get("count", 0))

    if cfg.session_limit and session_used >= cfg.session_limit:
        return RateLimitResult(
            allowed=False,
            reason=f"本会话演示次数已用完（{session_used}/{cfg.session_limit}）。感谢体验。",
            session_used=session_used,
            session_limit=cfg.session_limit,
            daily_used=daily_used,
            daily_limit=cfg.daily_limit,
        )

    if cfg.daily_limit and daily_used >= cfg.daily_limit:
        return RateLimitResult(
            allowed=False,
            reason=f"今日全站演示额度已用完（{daily_used}/{cfg.daily_limit}）。请明天再来。",
            session_used=session_used,
            session_limit=cfg.session_limit,
            daily_used=daily_used,
            daily_limit=cfg.daily_limit,
        )

    if cfg.cooldown_sec and last_ts > 0:
        elapsed = time.time() - last_ts
        if elapsed < cfg.cooldown_sec:
            wait = cfg.cooldown_sec - elapsed
            return RateLimitResult(
                allowed=False,
                reason=f"请求过于频繁，请 {wait:.0f} 秒后再试。",
                session_used=session_used,
                session_limit=cfg.session_limit,
                daily_used=daily_used,
                daily_limit=cfg.daily_limit,
                retry_after_sec=wait,
            )

    return RateLimitResult(
        allowed=True,
        session_used=session_used,
        session_limit=cfg.session_limit,
        daily_used=daily_used,
        daily_limit=cfg.daily_limit,
    )


def consume_rate_limit(
    *,
    app_name: str,
    session_state: dict,
    config: Optional[RateLimitConfig] = None,
) -> RateLimitResult:
    result = check_rate_limit(app_name=app_name, session_state=session_state, config=config)
    if not result.allowed:
        return result

    cfg = config or load_config(app_name)
    session_state["_demo_session_used"] = int(session_state.get("_demo_session_used", 0) or 0) + 1
    session_state["_demo_last_ts"] = time.time()

    if cfg.enabled:
        with _LOCK:
            daily = _read_daily(cfg.counter_path)
            daily["count"] = int(daily.get("count", 0)) + 1
            daily["date"] = _today()
            _write_daily(cfg.counter_path, daily)
            result.daily_used = daily["count"]

    result.session_used = int(session_state["_demo_session_used"])
    return result


def format_quota_caption(result: RateLimitResult, *, enabled: bool) -> str:
    if not enabled:
        return "演示限额：本地已关闭"
    return (
        f"演示限额：本会话 {result.session_used}/{result.session_limit}"
        f" · 今日全站 {result.daily_used}/{result.daily_limit}"
    )
