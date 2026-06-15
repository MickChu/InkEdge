"""
InkEdge Studio — Streamlit GUI

纯调度层：渲染界面，调用 src/ 下模块。
所有业务逻辑在 src/，GUI 不做独立处理。

启动方式:
    streamlit run studio.py
    python main.py studio
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.project_utils import get_project_list  # backward compat for tests

st.set_page_config(
    page_title="InkEdge Studio",
    page_icon="📚",
    layout="wide",
)

# ═══════════════════════════════════════
# 中文侧边栏导航
# ═══════════════════════════════════════
pages = [
    st.Page("pages/00_home.py", title="🏠 仪表盘", icon="📚"),
    st.Page("pages/01_new_project.py", title="📖 新建项目", icon="📖"),
    st.Page("pages/02_write.py", title="✍️ 写稿工作台", icon="✍️"),
    st.Page("pages/08_characters.py", title="👤 角色卡", icon="👤"),
    st.Page("pages/07_worldbuilding.py", title="🌍 世界观", icon="🌍"),
    st.Page("pages/06_state.py", title="⚔️ 角色状态", icon="⚔️"),
    st.Page("pages/03_style.py", title="🎨 风格管理", icon="🎨"),
    st.Page("pages/04_index.py", title="🔎 向量索引", icon="🔎"),
    st.Page("pages/05_check.py", title="🔍 质量校验", icon="🔍"),
]

pg = st.navigation(pages, position="sidebar")
pg.run()
