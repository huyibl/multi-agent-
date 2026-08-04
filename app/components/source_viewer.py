"""RAG 检索来源展示组件。"""

import streamlit as st

from health_assistant.schemas.response import HealthResponse


def render_source_viewer(response: HealthResponse | None) -> None:
    """展示检索来源、计算过程与评审状态。"""
    if not response:
        st.info("发送问题后，此处将展示检索来源与计算过程。")
        return

    st.subheader("计算过程")
    calc = response.calculations
    if calc:
        if calc.bmi:
            st.metric("BMI", f"{calc.bmi} ({calc.bmi_category})")
        if calc.protein_range_g:
            low, high = calc.protein_range_g
            st.metric("蛋白质建议", f"{low} - {high} g/天")
        if calc.tdee_kcal:
            st.metric("每日热量 (TDEE)", f"{calc.tdee_kcal} kcal")
    else:
        st.write("无计算结果")

    st.subheader("评审结果")
    status_color = "green" if response.review_status == "pass" else "orange"
    st.markdown(f":{status_color}[{response.review_status.upper()}]")
    if response.review_feedback:
        st.warning(response.review_feedback)

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
