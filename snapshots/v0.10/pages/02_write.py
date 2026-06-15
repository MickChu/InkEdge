"""
写稿工作台 — Streamlit 页面

左右分栏：控制面板 + 生成结果
支持两种模式：续写新章 / 改写旧章
对应 CLI: python main.py write / revise
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
    projects_dir = PROJECT_ROOT / "projects"
    if projects_dir.exists():
        names = [d.name for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
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

# ─── 模式切换 ───
mode = st.radio("模式", ["✍️ 写新章", "🔄 改写章节"], horizontal=True)

# ─── 获取已有章节 ───
ch_dir = project_dir / "chapters"
existing_chs = []
if ch_dir.exists():
    for f in ch_dir.iterdir():
        if f.suffix in (".md", ".txt"):
            try:
                num = int(f.stem.replace("chapter_", "").split("_")[0])
                existing_chs.append(num)
            except ValueError:
                # 中文命名如 0001_迭代 V2.md
                try:
                    num = int(f.stem[0:4])
                    existing_chs.append(num)
                except ValueError:
                    pass
existing_chs = sorted(set(existing_chs))
next_ch = max(existing_chs) + 1 if existing_chs else 1

# ─── AI 模型选择 ───
from src.utils.config import get_config
cfg = get_config()
models_cfg = cfg.get("models", {})
available_models = models_cfg.get("available", ["deepseek-v4-flash"])
default_model = models_cfg.get("primary", "deepseek-v4-flash")

# ─── 左侧控制栏 ───
left, right = st.columns([1, 2])

with left:
    st.subheader("⚙️ 控制面板")

    # 模型选择
    model_name = st.selectbox(
        "AI 模型",
        available_models,
        index=available_models.index(default_model) if default_model in available_models else 0,
        help="deepseek-v4-pro: 逻辑更强 / v4-flash: 速度快"
    )

    if mode == "✍️ 写新章":
        chapter_num = st.number_input("章节号", min_value=1,
                                       value=next_ch, step=1)
    else:
        chapter_num = st.selectbox(
            "章节号",
            existing_chs if existing_chs else [1],
            help="选择要改写的已写章节"
        )

    guidance = st.text_area(
        "写作指导" if mode == "✍️ 写新章" else "修改指导",
        placeholder="本章关键场景..." if mode == "✍️ 写新章" else "如：加强战斗描写、增加对话密度、精简环境描写",
        height=100
    )
    words_target = st.number_input("目标字数", min_value=500,
                                    max_value=10000, value=3000, step=500)

    # 卷纲（仅写新章时显示）
    if mode == "✍️ 写新章":
        vol_file = project_dir / "story" / "outlines" / f"volume_{(chapter_num - 1) // 10 + 1:02d}.md"
        if vol_file.exists():
            with st.expander("📋 卷纲"):
                volume_hint = vol_file.read_text(encoding="utf-8")[:2000]
                st.text_area("卷纲参考", volume_hint, height=150, disabled=True,
                             label_visibility="collapsed")

    # 执行按钮
    btn_label = "✍️ 生成本章" if mode == "✍️ 写新章" else "🔄 改写本章"
    if st.button(btn_label, type="primary", use_container_width=True):
        spinner_text = f"正在生成第{chapter_num}章..."
        if mode == "✍️ 写新章":
            with st.spinner(spinner_text):
                import asyncio
                from src.core.llm_client import LLMClient
                from src.agents.writer import WriterAgent

                # --model 运行时覆盖
                cfg.set("model_name", model_name)

                llm = LLMClient()
                writer = WriterAgent(project_dir=str(project_dir), llm_client=llm)
                vol_text = vol_file.read_text(encoding="utf-8") if vol_file.exists() else ""

                try:
                    result = asyncio.run(writer.write_chapter(
                        chapter_number=chapter_num,
                        words_target=words_target,
                        guidance=guidance,
                        volume_outline=vol_text,
                    ))
                    st.session_state["gen_content"] = result.get("content", "")
                    st.session_state["gen_chapter"] = chapter_num
                    st.session_state["gen_words"] = result.get("word_count", 0)
                except Exception as e:
                    st.error(f"生成失败: {e}")
        else:
            # 改写模式
            with st.spinner(f"正在改写第{chapter_num}章..."):
                import asyncio
                from src.core.base_agent import AgentContext
                from src.core.orchestrator import Orchestrator, PipelineStep
                from src.agents.revise import ReviseAgent

                cfg.set("model_name", model_name)

                context = AgentContext(
                    project_dir=str(project_dir),
                    user_guidance=guidance,
                    extra={
                        "chapter_number": chapter_num,
                        "word_count": words_target,
                    },
                )
                orch = Orchestrator(str(project_dir))
                reviser = ReviseAgent()
                steps = [PipelineStep(agent=reviser, required=True)]

                try:
                    result = asyncio.run(orch.run_sequential(steps, context))
                    if result.success and result.final_context:
                        updates = result.final_context.extra or {}
                        st.session_state["gen_content"] = updates.get("chapter_text", "")
                        st.session_state["gen_chapter"] = chapter_num
                        st.session_state["gen_words"] = updates.get("revised_length", 0)
                        st.session_state["revise_bak"] = updates.get("bak_path", "")
                    else:
                        st.error(f"改写失败: {result.error}")
                except Exception as e:
                    st.error(f"改写失败: {e}")

    # 生成结果（通用）
    if "gen_content" in st.session_state and st.session_state.get("gen_chapter") == chapter_num:
        word_label = "生成" if mode == "✍️ 写新章" else "改写完成"
        st.success(f"✅ {word_label} ({st.session_state['gen_words']} 字)")

        col_save, col_retry = st.columns(2)
        with col_save:
            save_label = "💾 保存" if mode == "✍️ 写新章" else "💾 覆盖原文件(已备份)"
            if st.button(save_label, use_container_width=True):
                ch_dir.mkdir(parents=True, exist_ok=True)
                # 改写模式：备份已在 ReviseAgent 中完成，这里只写新内容
                if mode == "✍️ 写新章":
                    ch_file = ch_dir / f"{chapter_num:04d}.md"
                    ch_file.write_text(st.session_state["gen_content"], encoding="utf-8")
                    st.success(f"已保存: {ch_file}")
                else:
                    # 改写已由 ReviseAgent 完成保存+备份
                    st.success(f"第{chapter_num}章已更新，备份为 .bak")
                del st.session_state["gen_content"]
                st.rerun()
        with col_retry:
            retry_label = "🔄 重写" if mode == "✍️ 写新章" else "🔄 重新改写"
            if st.button(retry_label, use_container_width=True):
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

    # 生成结果 / 已有章节展示
    if "gen_content" in st.session_state and st.session_state.get("gen_chapter") == chapter_num:
        st.subheader(f"📝 第{chapter_num}章正文")
        st.text_area("正文", st.session_state["gen_content"],
                     height=600, label_visibility="collapsed")
    else:
        # 显示已有章节（改写模式下自动加载原文）
        if ch_dir.exists():
            candidates = [
                ch_dir / f"chapter_{chapter_num:04d}.md",
                ch_dir / f"chapter_{chapter_num:04d}.txt",
            ]
            for c in candidates:
                if c.exists():
                    st.subheader(f"📄 第{chapter_num}章 (当前版本)")
                    st.text_area("正文", c.read_text(encoding="utf-8"),
                                 height=600, disabled=True, label_visibility="collapsed")
                    break
            else:
                # 模糊匹配
                for fname in sorted(ch_dir.iterdir()):
                    if fname.name.startswith(f"{chapter_num:04d}") and fname.suffix in (".md", ".txt"):
                        st.subheader(f"📄 第{chapter_num}章 (当前版本)")
                        st.text_area("正文", fname.read_text(encoding="utf-8"),
                                     height=600, disabled=True, label_visibility="collapsed")
                        break
                else:
                    st.info("选择参数后点击按钮开始")
        else:
            st.info("选择参数后点击按钮开始")

floating_home()
