"""RAG 检索来源与 Agent 思考过程展示。"""

import streamlit as st

from app.components.trace_viewer import render_trace_viewer
from health_assistant.schemas.response import HealthResponse


def render_source_viewer(response: HealthResponse | None) -> None:
    """展示思考过程、计算、评审与检索来源。"""
    trace = None
    if response and response.metadata:
        trace = response.metadata.get("trace")
    if not trace:
        trace = st.session_state.get("agent_trace")

    render_trace_viewer(trace)

    if not response:
        st.info("发送问题后，此处将展示计算过程与检索来源。")
        return

    st.subheader("计算过程")
    calc = response.calculations
    if calc and (calc.bmi or calc.protein_range_g or calc.tdee_kcal):
        if calc.bmi:
            st.metric("BMI", f"{calc.bmi} ({calc.bmi_category})")
        if calc.protein_range_g:
            low, high = calc.protein_range_g
            st.metric("蛋白质建议", f"{low} - {high} g/天")
        if calc.tdee_kcal:
            st.metric("每日热量 (TDEE)", f"{calc.tdee_kcal} kcal")
    else:
        st.caption("暂无计算值。在对话中补充身高体重后可自动计算。")

    st.subheader("评审结果")
    status_color = "green" if response.review_status == "pass" else "orange"
    st.markdown(f":{status_color}[{response.review_status.upper()}]")
    if response.review_feedback:
        st.warning(response.review_feedback)

    llm_calls = (response.metadata or {}).get("llm_calls")
    if llm_calls is not None:
        st.caption(f"本次 LLM 调用次数: {llm_calls}")

    st.subheader("检索来源")
    if response.retrieved_chunks:
        for i, chunk in enumerate(response.retrieved_chunks, 1):
            with st.expander(f"[{i}] {chunk.source} ({chunk.doc_type})"):
                st.write(chunk.content)
    elif response.citations:
        for c in response.citations:
            st.write(f"- {c}")
    else:
        st.write("无检索结果")
