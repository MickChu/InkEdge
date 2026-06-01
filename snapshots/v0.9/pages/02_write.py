"""
写稿工作台 — Streamlit 页面

左右分栏：控制面板 + 上下文预览/生成结果
对应 CLI: python main.py write
"""
import sys, os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="写稿 · InkEdge", page_icon="✍️", layout="wide")

# ─── 获取项目参数 ───
q = st.query_params
proj_name = q.get("name", "")

if not proj_name:
    # 列出可选项目
    projects_dir = PROJECT_ROOT / "projects"
    if projects_dir.exists():
        names = [d.name for d in projects_dir.iterdir() if d.is_dir()]
    else:
        names = []
    proj_name = st.selectbox("选择项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    floating_home()
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
if not project_dir.exists():
    st.error(f"项目不存在: {proj_name}")
    st.stop()

st.title(f"✍️ 写稿工作台: {proj_name}")

# ─── 获取已有章节 ───
ch_dir = project_dir / "chapters"
existing_chs = sorted([int(f.stem) for f in ch_dir.glob("*.md")]) if ch_dir.exists() else []
next_ch = max(existing_chs) + 1 if existing_chs else 1

# ─── 左侧控制栏 ───
left, right = st.columns([1, 2])

with left:
    st.subheader("⚙️ 控制面板")

    chapter_num = st.number_input("章节号", min_value=1,
                                   value=next_ch, step=1)
    guidance = st.text_area("写作指导",
                             placeholder="本章关键场景、伏笔推进、对白要点...",
                             height=100)
    words_target = st.number_input("目标字数", min_value=500,
                                    max_value=10000, value=3000, step=500)

    # 读取卷纲供用户参考
    vol_file = project_dir / "story" / "outlines" / f"volume_{(chapter_num - 1) // 10 + 1:02d}.md"
    volume_hint = ""
    if vol_file.exists():
        with st.expander("📋 卷纲"):
            volume_hint = vol_file.read_text(encoding="utf-8")[:2000]
            st.text_area("卷纲参考", volume_hint, height=150, disabled=True,
                         label_visibility="collapsed")

    if st.button("✍️ 生成本章", type="primary", use_container_width=True):
        with st.spinner(f"正在生成第{chapter_num}章... (约30-60秒)"):
            import asyncio
            from src.core.llm_client import LLMClient
            from src.agents.writer import WriterAgent
            from src.utils.file_io import read_file

            llm = LLMClient()
            writer = WriterAgent(project_dir=str(project_dir), llm_client=llm)

            # 读取卷纲
            vol_text = vol_file.read_text(encoding="utf-8") if vol_file.exists() else ""

            try:
                result = asyncio.run(writer.write_chapter(
                    chapter_number=chapter_num,
                    words_target=words_target,
                    guidance=guidance,
                    volume_outline=vol_text,
                ))
                # 保存生成结果到 session
                st.session_state["gen_content"] = result.get("content", "")
                st.session_state["gen_chapter"] = chapter_num
                st.session_state["gen_words"] = result.get("word_count", 0)
            except Exception as e:
                st.error(f"生成失败: {e}")
                st.exception(e)

    # 之前生成的结果
    if "gen_content" in st.session_state and st.session_state.get("gen_chapter") == chapter_num:
        st.success(f"✅ 第{chapter_num}章已生成 ({st.session_state['gen_words']} 字)")

        col_save, col_retry = st.columns(2)
        with col_save:
            if st.button("💾 保存", use_container_width=True):
                ch_dir.mkdir(parents=True, exist_ok=True)
                ch_file = ch_dir / f"{chapter_num:04d}.md"
                ch_file.write_text(st.session_state["gen_content"], encoding="utf-8")
                st.success(f"已保存: {ch_file}")
                # 删除生成缓存
                del st.session_state["gen_content"]
                st.rerun()
        with col_retry:
            if st.button("🔄 重写", use_container_width=True):
                del st.session_state["gen_content"]
                st.rerun()

# ─── 右侧预览 ───
with right:
    # 上下文预览
    with st.expander("📋 章节上下文预览", expanded=False):
        try:
            from src.agents.writer import ContextBuilder
            cb = ContextBuilder(str(project_dir))
            context = cb.build(chapter_number=chapter_num, max_chars=2000)
            st.text_area("上下文", context, height=300, disabled=True,
                         label_visibility="collapsed")
        except Exception as e:
            st.caption(f"上下文加载失败: {e}")

    # 生成结果展示
    if "gen_content" in st.session_state and st.session_state.get("gen_chapter") == chapter_num:
        st.subheader(f"📝 第{chapter_num}章正文")
        st.text_area("正文", st.session_state["gen_content"],
                     height=600, label_visibility="collapsed")
    else:
        # 显示已有章节
        existing_file = ch_dir / f"{chapter_num:04d}.md"
        if existing_file.exists():
            st.subheader(f"📄 第{chapter_num}章 (已保存)")
            st.text_area("正文", existing_file.read_text(encoding="utf-8"),
                         height=600, disabled=True, label_visibility="collapsed")
        else:
            st.info("选择参数后点击「生成本章」")

floating_home()
