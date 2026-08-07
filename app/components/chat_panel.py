"""对话面板：多轮健身咨询，会话档案从对话中自动累积。"""

import streamlit as st

from health_assistant.schemas.user_profile import UserProfile
from health_assistant.services.chat_service import ChatService

EXAMPLE_QUERIES = [
    "我身高172，体重70，想增肌，每天吃多少蛋白质？",
    "那碳水大概吃多少？",
    "减脂期蛋白质和训练怎么安排？",
]


def _get_chat_service() -> ChatService:
    """返回 session 内复用的 ChatService 单例。"""
    if "chat_service" not in st.session_state:
        st.session_state.chat_service = ChatService()
    return st.session_state.chat_service


def _get_profile() -> UserProfile:
    """读取会话档案；兼容 dict 反序列化，脏数据不崩。"""
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = UserProfile()
    profile = st.session_state.user_profile
    if isinstance(profile, dict):
        try:
            profile = UserProfile(**profile)
        except Exception:
            profile = UserProfile().merge_from_entities(profile)
        st.session_state.user_profile = profile
    return profile


def init_chat_state() -> None:
    """初始化消息列表、上次响应与 Agent Trace。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "agent_trace" not in st.session_state:
        st.session_state.agent_trace = []


def render_chat_history() -> None:
    """渲染示例问题与历史消息（不含输入框）。"""
    init_chat_state()

    st.caption("直接提问即可。可先说出身高/体重/目标；后续追问会记住上文。")
    cols = st.columns(len(EXAMPLE_QUERIES))
    for i, q in enumerate(EXAMPLE_QUERIES):
        if cols[i].button(q[:12] + "…", key=f"ex_{i}", use_container_width=True):
            st.session_state["_pending_prompt"] = q
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def handle_user_prompt(prompt: str) -> None:
    """处理一轮用户输入（在 chat_input 吸底后由主页面调用）。"""
    init_chat_state()
    history_before = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        service = _get_chat_service()
        profile = _get_profile()
        live_trace: list[dict] = []
        answer_parts: list[str] = []

        try:
            status = st.status("教练团队处理中…", expanded=True)
            answer_box = st.empty()

            for event in service.ask_events(
                prompt,
                profile=profile,
                history=history_before,
            ):
                etype = event.get("type")

                if etype == "profile":
                    st.session_state.user_profile = event["profile"]

                elif etype == "trace":
                    te = event["event"]
                    replaced = False
                    for i in range(len(live_trace) - 1, -1, -1):
                        if (
                            live_trace[i].get("step") == te.get("step")
                            and live_trace[i].get("status") == "running"
                        ):
                            live_trace[i] = te
                            replaced = True
                            break
                    if not replaced:
                        live_trace.append(te)
                    st.session_state.agent_trace = list(live_trace)

                    with status:
                        status.update(
                            label=f"{te.get('title', '处理中')}…",
                            state="running",
                        )
                        for item in live_trace:
                            icon = "✅" if item.get("status") == "done" else "⏳"
                            llm_tag = ""
                            if item.get("used_llm") is True:
                                llm_tag = " · LLM"
                            elif item.get("used_llm") is False:
                                llm_tag = " · 规则/工具"
                            lat = (
                                f" · {item['latency_ms']:.0f}ms"
                                if item.get("latency_ms") is not None
                                else ""
                            )
                            st.write(
                                f"{icon} **{item.get('title')}**{llm_tag}{lat}  \n"
                                f"{item.get('detail', '')}"
                            )

                elif etype == "token":
                    answer_parts.append(event["text"])
                    answer_box.markdown("".join(answer_parts))

                elif etype == "done":
                    response = event["response"]
                    st.session_state.last_response = response
                    st.session_state.agent_trace = response.metadata.get(
                        "trace", live_trace
                    )
                    if response.metadata.get("profile"):
                        try:
                            st.session_state.user_profile = UserProfile(
                                **{
                                    k: v
                                    for k, v in response.metadata["profile"].items()
                                    if k in UserProfile.model_fields
                                }
                            )
                        except Exception:
                            pass
                    answer_box.markdown(response.answer)
                    status.update(label="完成", state="complete")
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response.answer}
                    )

        except Exception as e:
            # 兜底：任意异常也要给出助手气泡，避免只剩红条
            fallback = (
                "这轮没能完整处理，请换种说法再试，例如：\n"
                "「我身高172体重70，想增肌，蛋白怎么吃？」\n\n"
                f"（内部提示：{e}）\n\n"
                "> 仅供健身营养参考，不构成医疗建议。"
            )
            st.markdown(fallback)
            st.session_state.messages.append(
                {"role": "assistant", "content": fallback}
            )


def render_chat_panel() -> None:
    """兼容旧调用名，等同于 ``render_chat_history``。"""
    render_chat_history()
