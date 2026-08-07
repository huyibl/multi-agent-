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
from health_assistant.services.ingest_service import IngestService
from health_assistant.utils.sqlite_patch import sqlite_info

clear_settings_cache()
settings = get_settings()

try:
    admin_mode = st.query_params.get("admin") == "1"
except Exception:
    admin_mode = False

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
            "Cloud 使用内存向量库：每次 **Reboot 后需重新点重建**；"
            "成功或失败都会显示在按钮下方。"
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

        if st.button("重建向量库", type="primary"):
            with st.spinner("正在入库..."):
                try:
                    result = IngestService().run()
                    if result.get("stored", 0) <= 0:
                        st.session_state["ingest_feedback"] = {
                            "ok": False,
                            "text": (
                                f"入库未写入数据：加载 {result.get('loaded', 0)} 页，"
                                f"切块 {result.get('chunks', 0)}。"
                                " 请确认仓库中存在 `data/raw/` 文档。"
                            ),
                        }
                    else:
                        st.session_state["ingest_feedback"] = {
                            "ok": True,
                            "text": (
                                f"重建成功：加载 {result['loaded']} 页，"
                                f"生成 {result['chunks']} 块，存储 {result['stored']} 条。"
                                f" 路径: {settings.chroma_persist_dir}"
                            ),
                        }
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
prompt = st.session_state.pop("_pending_prompt", None)
if prompt is None:
    prompt = st.chat_input("例如：我身高172体重70想增肌，蛋白质吃多少？")

if prompt:
    handle_user_prompt(prompt)
