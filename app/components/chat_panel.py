"""对话面板组件。"""

import streamlit as st

from health_assistant.schemas.user_profile import UserProfile
from health_assistant.services.chat_service import ChatService


def _get_chat_service() -> ChatService:
    """懒加载 ChatService 单例，避免每条消息重建 Graph。"""
    if "chat_service" not in st.session_state:
        st.session_state.chat_service = ChatService()
    return st.session_state.chat_service


def render_chat_panel(profile: UserProfile) -> None:
    """渲染带消息历史的对话界面（支持流式 Markdown 输出）。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("请输入健康相关问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            service = _get_chat_service()
            try:
                with st.spinner("规划中 → 检索/计算 → 生成回答..."):
                    def _stream():
                        for token in service.ask_stream(prompt, profile=profile):
                            yield token

                    st.write_stream(_stream)

                if service.last_response:
                    st.session_state.last_response = service.last_response
                    # 历史记录存 Markdown 正文，不存 JSON
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": service.last_response.answer,
                        }
                    )
            except Exception as e:
                st.error(f"处理失败: {e}")
