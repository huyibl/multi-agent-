"""对话面板组件。"""

import streamlit as st

from health_assistant.schemas.response import HealthResponse
from health_assistant.schemas.user_profile import UserProfile
from health_assistant.services.chat_service import ChatService


def render_chat_panel(profile: UserProfile) -> None:
    """渲染带消息历史的对话界面。"""
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
            with st.spinner("多 Agent 协作处理中..."):
                try:
                    service = ChatService()
                    response = service.ask(prompt, profile=profile)
                    st.session_state.last_response = response
                    st.markdown(response.answer)
                except Exception as e:
                    st.error(f"处理失败: {e}")
                    response = None

        if response:
            st.session_state.messages.append({"role": "assistant", "content": response.answer})
