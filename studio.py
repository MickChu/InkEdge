"""
InkEdge Studio — Streamlit GUI

纯调度层：渲染界面，调用 src/ 下模块。
所有业务逻辑在 src/，GUI 不做独立处理。

启动方式:
    streamlit run studio.py
    python main.py studio
"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 Python path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="InkEdge Studio",
    page_icon="📚",
    layout="wide",
)


def get_project_list():
    """获取所有项目列表（纯调度：调用 StateManager）"""
    projects_dir = PROJECT_ROOT / "projects"
    if not projects_dir.exists():
        return []
    projects = []
    for d in projects_dir.iterdir():
        if d.is_dir():
            fm = d / "foundation" / "unified_foundation.md"
            ch_dir = d / "chapters"
            ch_count = len(list(ch_dir.glob("*.md"))) if ch_dir.exists() else 0
            projects.append({
                "name": d.name,
                "has_foundation": fm.exists(),
                "chapter_count": ch_count,
                "path": str(d),
            })
    return sorted(projects, key=lambda p: p["name"])


def dashboard():
    """项目仪表盘"""
    st.title("📚 InkEdge Studio")
    st.caption("AI 辅助长篇小说创作框架")

    projects = get_project_list()

    if not projects:
        st.info("还没有项目。点击下方按钮创建你的第一本书。")
        st.page_link("pages/01_new_project.py", label="📖 新建项目")
        return

    # 项目卡片网格
    cols = st.columns(3)
    for i, proj in enumerate(projects):
        with cols[i % 3]:
            with st.container(border=True):
                status = "✅ 已建书" if proj["has_foundation"] else "⏳ 待建书"
                st.subheader(f"📖 {proj['name']}")
                st.caption(f"{status} · 已写 {proj['chapter_count']} 章")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.page_link("pages/02_write.py",
                                 label="✍️ 写稿",
                                 help="打开写稿工作台")
                with col_b:
                    if proj["has_foundation"]:
                        st.page_link("pages/05_check.py",
                                     label="🔍 校验",
                                     help="质量校验")
                    else:
                        st.button("⏳", disabled=True, key=f"chk_{proj['name']}", help="需要先建书")

                # 更多操作
                with st.expander("更多"):
                    st.page_link("pages/03_style.py", label="🎨 风格管理")
                    st.page_link("pages/04_index.py", label="🔎 向量索引")
                    st.page_link("pages/06_state.py", label="⚔️ 角色状态")

    # 底部操作栏
    st.divider()
    col_new, col_sys = st.columns([1, 3])
    with col_new:
        st.page_link("pages/01_new_project.py", label="📖 新建项目", use_container_width=True)
    with col_sys:
        try:
            from src.core.config import ConfigManager
            cfg = ConfigManager()
            model = cfg.get("llm.model", "未配置")
            st.caption(f"LLM: {model} · Python 3.11")
        except Exception:
            st.caption("LLM: 未配置")


if __name__ == "__main__":
    dashboard()

# 页面路由说明:
# Streamlit pages/ 目录下的文件自动注册为子页面
# - pages/01_new_project.py  → /01_new_project
# - pages/02_write.py        → /02_write
# - pages/03_style.py        → /03_style
# - pages/04_index.py        → /04_index
# - pages/05_check.py        → /05_check
# - pages/06_state.py        → /06_state
