"""
世界观设定 — Streamlit 页面

查看和编辑项目世界观文件（world_building.md / core_seed.md / plot_architecture.md）
"""
import sys, os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="世界观 · InkEdge", page_icon="🌍")

floating_home()
st.title("🌍 世界观设定")

# ─── 项目列表 ───
projects_dir = PROJECT_ROOT / "projects"
if not projects_dir.exists():
    st.info("还没有项目。先去「📖 新建项目」创建一个。")
    st.stop()

project_names = sorted([
    d.name for d in projects_dir.iterdir()
    if d.is_dir() and not d.name.startswith(".")
])

if not project_names:
    st.info("还没有项目。先去「📖 新建项目」创建一个。")
    st.stop()

selected = st.selectbox("选择项目", project_names)
project_dir = projects_dir / selected

# ─── 世界观文件 ───
files = {
    "world_building.md": "世界观构建",
    "core_seed.md": "核心种子",
    "plot_architecture.md": "情节架构",
}
existing = {}

for fname, label in files.items():
    fpath = project_dir / fname
    if fpath.exists():
        existing[label] = fpath

if not existing:
    st.warning("该项目还没有世界观文件。\n\n请使用交互式建书向导（`python main.py new --wizard`）或直接在「📖 新建项目」页面用交互模式生成。")
    st.stop()

tab_names = list(existing.keys())
tabs = st.tabs(tab_names)

for tab, (label, fpath) in zip(tabs, existing.items()):
    with tab:
        content = fpath.read_text(encoding="utf-8")
        st.caption(f"文件: `{fpath.name}` · {len(content)} 字")

        col1, col2 = st.columns([5, 1])
        with col1:
            edited = st.text_area(
                "编辑内容",
                value=content,
                height=500,
                key=f"edit_{label}",
                label_visibility="collapsed",
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("💾 保存", key=f"save_{label}", use_container_width=True):
                fpath.write_text(edited, encoding="utf-8")
                st.success("已保存")
                st.rerun()

            # 字数统计
            st.metric("字数", len(edited))
            st.metric("段落", edited.count("\n\n") + 1)
