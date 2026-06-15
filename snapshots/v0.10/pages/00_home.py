"""
仪表盘 — 首页
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="InkEdge Studio", page_icon="📚", layout="wide")

st.title("📚 InkEdge Studio")
st.caption("AI 辅助长篇小说创作框架")

from src.utils.project_utils import get_project_list
projects = get_project_list(PROJECT_ROOT / "projects")

if not projects:
    st.info("还没有项目。去「📖 新建项目」创建你的第一本书吧。")
else:
    cols = st.columns(3)
    for i, proj in enumerate(projects):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(f"📖 {proj['name']}")
                parts = []
                if proj["has_foundation"]:
                    parts.append("✅ 已建书")
                else:
                    parts.append("⏳ 待建书")
                parts.append(f"已写 {proj['chapter_count']} 章")
                st.caption(" · ".join(parts))

                col_a, col_b = st.columns(2)
                with col_a:
                    st.page_link("pages/02_write.py", label="✍️ 写稿")
                with col_b:
                    if proj["has_foundation"]:
                        st.page_link("pages/05_check.py", label="🔍 校验")
                    else:
                        st.button("⏳", disabled=True, key=f"chk_{proj['name']}")

                with st.expander("更多设定"):
                    if proj["has_world"]:
                        st.page_link("pages/07_worldbuilding.py", label="🌍 世界观")
                    if proj["has_roles"]:
                        st.page_link("pages/08_characters.py", label="👤 角色卡")
                    st.page_link("pages/03_style.py", label="🎨 风格")
                    st.page_link("pages/04_index.py", label="🔎 索引")
                    st.page_link("pages/06_state.py", label="⚔️ 状态")

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
