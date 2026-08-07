"""Streamlit 主应用：对话优先的 AI 健身教练 UI（侧边栏档案 / Trace / 来源）。"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# 内联补丁：不依赖 config.*（Cloud 上 config 包名易冲突导致 ImportError）
try:
    import pysqlite3  # type: ignore

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st

# 必须是第一个 Streamlit 命令，否则会触发 SessionInfo 未初始化
st.set_page_config(
    page_title="AI 健身教练",
    page_icon="💪",
    layout="wide",
)

from config.bootstrap import (
    apply_streamlit_secrets,
    is_streamlit_cloud,
    prepare_runtime,
)

apply_streamlit_secrets()
prepare_runtime()
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("EMBEDDING_PROVIDER", "dashscope")

from app.components.chat_panel import handle_user_prompt, render_chat_history
from app.components.source_viewer import render_source_viewer
from config.settings import clear_settings_cache, get_settings
from health_assistant.services.kb_bootstrap import ensure_kb_ready, kb_status
from health_assistant.utils.sqlite_patch import sqlite_info

clear_settings_cache()
settings = get_settings()


@st.cache_resource(show_spinner="首次准备知识库中（约需数十秒，之后访客可直接提问）…")
def _warm_knowledge_base() -> dict:
    """进程级缓存：冷启动自动入库，访客无需点重建。"""
    return ensure_kb_ready()


try:
    admin_mode = st.query_params.get("admin") == "1"
except Exception:
    admin_mode = False

# Cloud / 本地均可预热；已有库则秒级返回
kb_info = _warm_knowledge_base()

# ---------- 侧边栏：档案 + 思考过程 ----------
with st.sidebar:
    st.markdown("### 会话档案")
    profile = st.session_state.get("user_profile")
    if profile:
        ctx = profile.to_context() if hasattr(profile, "to_context") else profile
        st.write(
            f"- 身高: {ctx.get('height_cm') or '未提供'}\n"
            f"- 体重: {ctx.get('weight_kg') or '未提供'}\n"
            f"- 目标: {ctx.get('goal') or '未提供'}"
        )
        st.caption("档案从对话中自动累积，追问时会自动沿用。")
    else:
        st.caption("还没有档案。在对话里说出身高体重和目标即可。")

    if st.button("清空对话与档案"):
        for key in ("messages", "user_profile", "last_response", "agent_trace"):
            st.session_state.pop(key, None)
        st.rerun()

    st.divider()
    render_source_viewer(st.session_state.get("last_response"))

    st.divider()
    st.caption(f"Embedding: `{settings.embedding_provider}`")
    st.caption(
        "LLM: "
        + ("已配置" if settings.deepseek_api_key else "未配置（规则兜底）")
    )
    if is_streamlit_cloud():
        st.caption("运行环境: Streamlit Cloud")
    if kb_info.get("ready"):
        st.caption(f"知识库: 已就绪（{kb_info.get('stored', 0)} 条）")
    else:
        st.caption(f"知识库: 未就绪 — {kb_info.get('error') or '请检查 Embedding Key'}")

    from app.rate_limit import check_rate_limit, format_quota_caption, load_config

    _rl_cfg = load_config("health_assistant")
    _rl = check_rate_limit(
        app_name="health_assistant", session_state=st.session_state, config=_rl_cfg
    )
    st.caption(format_quota_caption(_rl, enabled=_rl_cfg.enabled))
    if _rl_cfg.enabled and not _rl.allowed:
        st.warning(_rl.reason)

    st.caption("免责声明：仅供健身营养参考，不构成医疗建议。")

# ---------- 主区：标题 + 消息列表 ----------
st.title("AI 健身教练")
st.caption(
    "多 Agent + RAG | 直接对话即可，身高体重等可在聊天里说 |"
    " 仅供参考，不构成医疗建议"
)

if admin_mode:
    tab_chat, tab_kb = st.tabs(["健身对话", "知识库管理（管理员）"])
    with tab_chat:
        render_chat_history()
    with tab_kb:
        st.subheader("私人知识库入库")
        st.write(
            "正常访客打开页面会 **自动入库**，无需操作。"
            " 此处仅用于强制重建（例如更新了 `data/raw`）。"
        )
        st.caption(
            f"模式: `{'Ephemeral(Cloud)' if is_streamlit_cloud() else 'Persistent'}` | "
            f"目录: `{settings.chroma_persist_dir}`"
        )
        info = sqlite_info()
        st.caption(
            f"SQLite: {info.get('sqlite_version')} | pysqlite3 补丁: "
            f"{'已启用' if info.get('patched') else '未启用'}"
        )
        st.caption(f"当前状态: {kb_status()}")

        if st.button("强制重建向量库", type="primary"):
            with st.spinner("正在入库..."):
                try:
                    _warm_knowledge_base.clear()
                    result = ensure_kb_ready(force=True)
                    if not result.get("ready"):
                        st.session_state["ingest_feedback"] = {
                            "ok": False,
                            "text": f"重建失败：{result.get('error') or result}",
                        }
                    else:
                        st.session_state["ingest_feedback"] = {
                            "ok": True,
                            "text": (
                                f"重建成功：加载 {result.get('loaded', '?')} 页，"
                                f"切块 {result.get('chunks', '?')}，"
                                f"存储 {result.get('stored', 0)} 条。"
                            ),
                        }
                    _warm_knowledge_base()
                except Exception as exc:
                    st.session_state["ingest_feedback"] = {
                        "ok": False,
                        "text": f"重建失败：{exc}",
                    }

        feedback = st.session_state.get("ingest_feedback")
        if feedback:
            if feedback.get("ok"):
                st.success(feedback["text"])
            else:
                st.error(feedback["text"])
else:
    render_chat_history()

# ---------- 输入框必须在页面根级，才会固定在视口底部 ----------
from app.rate_limit import check_rate_limit, load_config as _load_rl

_prompt_cfg = _load_rl("health_assistant")
_prompt_quota = check_rate_limit(
    app_name="health_assistant", session_state=st.session_state, config=_prompt_cfg
)
_chat_disabled = _prompt_cfg.enabled and not _prompt_quota.allowed

prompt = st.session_state.pop("_pending_prompt", None)
if prompt is None and not _chat_disabled:
    prompt = st.chat_input("例如：我身高172体重70想增肌，蛋白质吃多少？")
elif _chat_disabled:
    st.chat_input("演示额度已用完，请稍后再试", disabled=True)

if prompt:
    handle_user_prompt(prompt)
