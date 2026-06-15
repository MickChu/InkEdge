"""
环境诊断 — Streamlit 页面

对应 CLI: python main.py doctor
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="环境诊断 · InkEdge", page_icon="🩺", layout="wide")
floating_home()

st.title("🩺 环境诊断")
st.caption("检查 Python 环境、依赖、配置、API 连通性和项目健康状态")

# ─── 检查范围 ───
col1, col2 = st.columns([3, 1])
with col1:
    check_scope = st.radio(
        "检查范围",
        ["全检", "仅 API 连通性"],
        horizontal=True,
        help="全检: 环境 + 配置 + API + 项目 / 仅API: 只测 LLM 连通"
    )
with col2:
    if st.button("🩺 运行诊断", type="primary", use_container_width=True):
        st.rerun()

# ─── 执行检查 ───
if st.session_state.get("_doctor_cache"):
    report = st.session_state["_doctor_cache"]
else:
    with st.spinner("正在检查..."):
        from src.doctor import DoctorOrchestrator
        api_only = (check_scope == "仅 API 连通性")
        orch = DoctorOrchestrator(api_only=api_only)
        report = orch.run()
        st.session_state["_doctor_cache"] = report

# ─── 环境层 ───
st.subheader("🔧 环境层")
env_checks = [c for c in report.checks if c.layer == "环境层"]
for c in env_checks:
    icon = "❌" if c.severity == "error" else ("⚠️" if c.severity == "warning" else "✅")
    with st.expander(f"{icon} {c.label} — {c.detail}", expanded=(c.severity == "error")):
        if c.hint:
            st.info(c.hint)

# ─── 配置层 ───
st.subheader("⚙️ 配置层")
cfg_checks = [c for c in report.checks if c.layer == "配置层"]
for c in cfg_checks:
    icon = "❌" if c.severity == "error" else ("⚠️" if c.severity == "warning" else "✅")
    with st.expander(f"{icon} {c.label} — {c.detail}", expanded=(c.severity == "error")):
        if c.hint:
            st.info(c.hint)

# ─── 连接层 ───
st.subheader("🌐 连接层")
api_checks = [c for c in report.checks if c.layer == "连接层"]
for c in api_checks:
    icon = "❌" if c.severity == "error" else ("⚠️" if c.severity == "warning" else "✅")
    with st.expander(f"{icon} {c.label} — {c.detail}", expanded=(c.severity == "error")):
        if c.hint:
            st.info(c.hint)

# ─── 项目层 ───
st.subheader("📖 项目层")
proj_checks = [c for c in report.checks if c.layer == "项目层"]
for c in proj_checks:
    icon = "❌" if c.severity == "error" else ("⚠️" if c.severity == "warning" else "✅")
    with st.expander(f"{icon} {c.label} — {c.detail}", expanded=(c.severity == "error")):
        if c.hint:
            st.info(c.hint)

# ─── 汇总 ───
st.divider()
if report.healthy:
    st.success(f"🎉 全部通过! 0 错误 / {len(report.warnings)} 警告 / {len(report.checks)} 检查")
else:
    st.error(f"❌ {len(report.errors)} 个错误 / {len(report.warnings)} 个警告 / {len(report.checks)} 检查")

# ─── 清除缓存按钮 ───
if st.button("🔄 重新检查"):
    st.session_state.pop("_doctor_cache", None)
    st.rerun()
