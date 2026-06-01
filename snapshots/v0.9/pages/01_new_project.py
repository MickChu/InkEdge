"""
新建项目 — Streamlit 页面

支持两种模式：
  - 一键建书：填写信息 → 开始建书（对应 CLI: python main.py new）
  - 交互式向导：逐步生成 → 每步审核修改（对应 CLI: python main.py new --wizard）
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import asyncio
import os
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="新建项目 · InkEdge", page_icon="📖")

# ═══════════════════════════════════════
# Session State 初始化
# ═══════════════════════════════════════
for key, default in [
    ("wizard_running", False),
    ("wizard_step_idx", 0),
    ("wizard_astate", None),
    ("wizard_step_names", []),
    ("wizard_total_steps", 0),
    ("wizard_output", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def _start_wizard(name, topic, genre, chapters, words):
    """初始化交互式向导"""
    from src.core.base_agent import AgentContext
    from src.agents.architect import ArchitectAgent

    project_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "projects", name
    )

    context = AgentContext(
        project_dir=project_dir,
        user_guidance=topic,
        extra={
            "genre": genre,
            "num_chapters": chapters,
            "word_number": words,
        },
    )

    arch = ArchitectAgent(template_name="snowflake")
    state = arch.wizard_init(context)

    st.session_state.wizard_astate = state
    st.session_state.wizard_step_names = [s.name for s in state["steps"]]
    st.session_state.wizard_total_steps = len(state["steps"])
    st.session_state.wizard_step_idx = 0
    st.session_state.wizard_running = True
    st.session_state.wizard_output = ""


def _run_wizard_step():
    """运行当前步骤的 LLM 生成"""
    from src.agents.architect import ArchitectAgent

    state = st.session_state.wizard_astate
    idx = st.session_state.wizard_step_idx

    arch = ArchitectAgent(template_name="snowflake")
    output = asyncio.run(arch.wizard_run_step(state, idx, retry=False))
    st.session_state.wizard_output = output
    st.session_state.wizard_astate = state


def _retry_wizard_step():
    """重新生成当前步骤"""
    from src.agents.architect import ArchitectAgent

    state = st.session_state.wizard_astate
    idx = st.session_state.wizard_step_idx

    arch = ArchitectAgent(template_name="snowflake")
    output = asyncio.run(arch.wizard_run_step(state, idx, retry=True))
    st.session_state.wizard_output = output
    st.session_state.wizard_astate = state


def _retry_with_feedback(feedback: str):
    """带修改意见重新生成"""
    from src.agents.architect import ArchitectAgent

    state = st.session_state.wizard_astate
    idx = st.session_state.wizard_step_idx

    arch = ArchitectAgent(template_name="snowflake")
    arch.wizard_set_feedback(state, idx, feedback)
    output = asyncio.run(arch.wizard_run_step(state, idx, retry=True))
    st.session_state.wizard_output = output
    st.session_state.wizard_astate = state


def _finalize_wizard():
    """完成向导，保存最终输出"""
    from src.agents.architect import ArchitectAgent

    arch = ArchitectAgent(template_name="snowflake")
    novel_setting = arch.wizard_finalize(st.session_state.wizard_astate)
    st.session_state.wizard_running = False
    return novel_setting


# ═══════════════════════════════════════
# 页面渲染
# ═══════════════════════════════════════

st.title("📖 新建项目")

# ─── 向导进行中 ───
if st.session_state.wizard_running:
    total = st.session_state.wizard_total_steps
    idx = st.session_state.wizard_step_idx
    names = st.session_state.wizard_step_names

    # 进度条
    st.progress((idx) / total, f"步骤 {idx+1}/{total}")
    st.header(f"📋 {names[idx]}")

    # 如果有上一步输出，显示（这里是我们刚生成的内容）
    if st.session_state.wizard_output:
        # 可编辑的文本区域 — 用户可以直接修改内容
        edited = st.text_area(
            "生成结果（可直接编辑）",
            value=st.session_state.wizard_output,
            height=400,
            key=f"wizard_edit_{idx}",
        )

        col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

        with col1:
            if st.button("✅ 确认继续", type="primary", use_container_width=True):
                # 如果用户直接编辑了文本，用编辑后的版本
                if edited != st.session_state.wizard_output:
                    state = st.session_state.wizard_astate
                    step = state["steps"][idx]
                    if step.output_key:
                        state["checkpoint"][step.output_key] = edited
                        # 也写文件
                        from src.utils.file_io import write_file
                        if step.output_file:
                            fpath = os.path.join(state["project_dir"], step.output_file)
                            write_file(fpath, edited)
                        # 持久化 checkpoint
                        arch = ArchitectAgent(template_name="snowflake")
                        arch._save_checkpoint(state["project_dir"], state["checkpoint"])
                    st.session_state.wizard_astate = state

                # 进入下一步
                if idx + 1 >= total:
                    name = _finalize_wizard()
                    st.success("🎉 建书完成！所有设定已保存。")
                    if st.button("✍️ 去写稿"):
                        st.switch_page("pages/02_write.py")
                    st.stop()

                st.session_state.wizard_step_idx = idx + 1
                st.session_state.wizard_output = ""
                _run_wizard_step()
                st.rerun()

        with col2:
            if st.button("🔄 重新生成", use_container_width=True):
                with st.spinner("重新生成中..."):
                    _retry_wizard_step()
                st.rerun()

        with col3:
            feedback = st.text_input("修改意见", placeholder="例：主角太弱了，给他一个隐藏背景",
                                     key=f"feedback_{idx}")
        with col4:
            if st.button("✏️ 提交", disabled=not feedback, use_container_width=True):
                with st.spinner("按修改意见重新生成..."):
                    _retry_with_feedback(feedback)
                st.rerun()

    else:
        # 首次进入 — 自动生成第一步
        with st.spinner(f"正在生成第 1 步: {names[0]}..."):
            _run_wizard_step()
        st.rerun()

    st.stop()


# ─── Step 1: 基本信息 ───
st.header("1️⃣ 基本信息")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("书名 *", placeholder="例: 大宋秘谍")
with col2:
    genre = st.selectbox("题材", [
        "历史架空", "奇幻", "科幻", "都市", "悬疑",
        "武侠", "仙侠", "言情", "军事", "轻小说",
    ])

topic = st.text_area("故事主题 *", placeholder="一句话描述你的故事核心。例: 北宋穿越者发现前穿越者已点歪科技树，需刹车",
                     height=80)

col3, col4 = st.columns(2)
with col3:
    chapters = st.number_input("目标章数", min_value=10, max_value=1000, value=60, step=10)
with col4:
    words_per = st.number_input("每章字数", min_value=1000, max_value=10000, value=3000, step=500)

# ─── Step 2: 写作方法 ───
st.header("2️⃣ 写作方法")
template = st.radio(
    "选择创作方法论",
    options=["unified", "snowflake"],
    format_func=lambda x: {
        "unified": "🌊 Unified（inkOS 风格）— 一次生成5段统一基础设定: 故事框架+卷纲+角色卡+书规+伏笔池",
        "snowflake": "❄️ Snowflake（雪花法）— 6步渐进式建书: 一句话→摘要→角色→扩展→设定→大纲",
    }[x],
    help="Unified 是默认推荐，更贴近 inkOS 工作流。Snowflake 更传统。"
)

wizard_mode = st.checkbox("🧙 交互式逐步建书", value=True,
                          help="每步生成后暂停，供你审核修改。关掉则一键生成全部。")

# ─── Step 3: 确认 ───
st.header("3️⃣ 确认")
if not name or not topic:
    st.warning("请先填写书名和故事主题")
else:
    mode_text = "交互式逐步模式（每步可审核修改）" if wizard_mode else f"一键生成（{template}）"
    st.info(f"""
    **书名**: {name}
    **题材**: {genre}
    **主题**: {topic}
    **目标**: {chapters}章 × {words_per}字 = {chapters * words_per:,}字
    **模式**: {mode_text}
    """)

    if st.button("🚀 开始建书", type="primary", use_container_width=True):
        if wizard_mode:
            _start_wizard(name, topic, genre, chapters, words_per)
            st.rerun()
        else:
            with st.spinner("正在生成统一基础设定... 这可能需要30-60秒"):
                import asyncio
                from src.core.base_agent import AgentContext
                from src.core.orchestrator import Orchestrator, PipelineStep
                from src.agents.architect import ArchitectAgent

                project_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "projects", name
                )

                context = AgentContext(
                    project_dir=project_dir,
                    user_guidance=topic,
                    extra={
                        "genre": genre,
                        "num_chapters": chapters,
                        "word_number": words_per,
                    },
                )

                orchestrator = Orchestrator(project_dir)
                architect = ArchitectAgent(template_name=template)
                steps = [PipelineStep(agent=architect, required=True)]

                result = asyncio.run(orchestrator.run_sequential(steps, context))
                if result.success:
                    st.success(f"✅ 建书完成！项目已创建: `projects/{name}/`")
                    st.page_link("pages/02_write.py", label="✍️ 去写稿 →")
                else:
                    st.error(f"建书失败: {result.error}")

floating_home()
