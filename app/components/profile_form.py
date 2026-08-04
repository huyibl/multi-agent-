"""用户档案表单组件。"""

import streamlit as st

from health_assistant.schemas.user_profile import ActivityLevel, HealthGoal, UserProfile


def render_profile_form() -> UserProfile:
    """渲染用户档案表单并返回 UserProfile。"""
    st.subheader("用户档案")
    col1, col2 = st.columns(2)
    with col1:
        height = st.number_input("身高 (cm)", min_value=100, max_value=250, value=172)
        weight = st.number_input("体重 (kg)", min_value=30, max_value=300, value=70)
        age = st.number_input("年龄", min_value=10, max_value=120, value=28)
    with col2:
        sex = st.selectbox("性别", ["male", "female"], format_func=lambda x: "男" if x == "male" else "女")
        activity = st.selectbox(
            "活动水平",
            [a.value for a in ActivityLevel],
            index=2,
            format_func=lambda x: {
                "sedentary": "久坐",
                "light": "轻度活动",
                "moderate": "中度活动",
                "active": "活跃",
                "very_active": "非常活跃",
            }.get(x, x),
        )
        goal = st.selectbox(
            "健康目标",
            [g.value for g in HealthGoal],
            index=3,
            format_func=lambda x: {
                "lose_weight": "减重",
                "maintain": "维持",
                "bulk": "增重",
                "muscle_gain": "增肌",
                "general_health": "一般健康",
            }.get(x, x),
        )

    return UserProfile(
        height_cm=float(height),
        weight_kg=float(weight),
        age=int(age),
        sex=sex,
        activity_level=ActivityLevel(activity),
        goal=HealthGoal(goal),
    )
