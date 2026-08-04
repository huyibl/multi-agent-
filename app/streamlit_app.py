"""Streamlit 主应用。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from app.components.chat_panel import render_chat_panel
from app.components.profile_form import render_profile_form
from app.components.source_viewer import render_source_viewer
from health_assistant.services.ingest_service import IngestService

st.set_page_config(
    page_title="个人健康管理助手",
    page_icon="🏥",
    layout="wide",
)

st.title("个人健康管理助手")
st.caption("RAG + 多 Agent 协作 | 仅供健康信息参考，不构成医疗建议")

tab_profile, tab_chat, tab_kb = st.tabs(["用户档案", "对话咨询", "知识库管理"])

with tab_profile:
    profile = render_profile_form()
    st.success("档案已就绪，可在「对话咨询」中使用。")

with tab_chat:
    col_main, col_side = st.columns([2, 1])
    with col_main:
        render_chat_panel(profile)
    with col_side:
        last = st.session_state.get("last_response")
        render_source_viewer(last)

with tab_kb:
    st.subheader("知识库管理")
    st.write("将 PDF/Markdown/CSV 文件放入 `data/raw/` 对应子目录后，点击下方按钮重建向量库。")
    if st.button("重建向量库", type="primary"):
        with st.spinner("正在入库..."):
            result = IngestService().run()
        st.success(f"完成：加载 {result['loaded']} 页，生成 {result['chunks']} 块，存储 {result['stored']} 条")

st.divider()
st.markdown(
    "<small>免责声明：本系统仅供健康信息参考，不构成医疗建议。"
    "如有特殊健康状况，请咨询专业医生或注册营养师。</small>",
    unsafe_allow_html=True,
)
