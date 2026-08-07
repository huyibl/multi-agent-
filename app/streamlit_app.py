"""Streamlit 主应用：对话优先的 AI 健身教练 UI（侧边栏档案 / Trace / 来源）。"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

# 必须是第一个 Streamlit 命令，否则会触发 SessionInfo 未初始化
st.set_page_config(
    page_title="AI 健身教练",
    page_icon="💪",
    layout="wide",
)

from config.bootstrap import apply_streamlit_secrets, is_streamlit_cloud

apply_streamlit_secrets()
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("EMBEDDING_PROVIDER", "dashscope")

from app.components.chat_panel import handle_user_prompt, render_chat_history
from app.components.source_viewer import render_source_viewer
from config.settings import clear_settings_cache, get_settings
from health_assistant.services.ingest_service import IngestService

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
        st.write("将 PDF/Markdown/CSV 放入 `data/raw/` 后重建向量库。普通用户无需此入口。")
        if st.button("重建向量库", type="primary"):
            with st.spinner("正在入库..."):
                result = IngestService().run()
            st.success(
                f"完成：加载 {result['loaded']} 页，生成 {result['chunks']} 块，"
                f"存储 {result['stored']} 条"
            )
else:
    render_chat_history()

# ---------- 输入框必须在页面根级，才会固定在视口底部 ----------
prompt = st.session_state.pop("_pending_prompt", None)
if prompt is None:
    prompt = st.chat_input("例如：我身高172体重70想增肌，蛋白质吃多少？")

if prompt:
    handle_user_prompt(prompt)
