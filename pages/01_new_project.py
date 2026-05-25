"""
新建项目 — Streamlit 页面

三步向导：基本信息 → 写作方法 → 建书确认
对应 CLI: python main.py new
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="新建项目 · InkEdge", page_icon="📖")
st.title("📖 新建项目")

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

# ─── Step 3: 确认 ───
st.header("3️⃣ 确认")
if not name or not topic:
    st.warning("请先填写书名和故事主题")
else:
    st.info(f"""
    **书名**: {name}
    **题材**: {genre}
    **主题**: {topic}
    **目标**: {chapters}章 × {words_per}字 = {chapters * words_per:,}字
    **方法**: {template}
    """)

    if st.button("🚀 开始建书", type="primary", use_container_width=True):
        with st.spinner("正在生成统一基础设定... 这可能需要30-60秒"):
            import asyncio
            from src.core.llm_client import LLMClient
            llm = LLMClient()

            # 调用 Architect
            from src.agents.architect import ArchitectAgent
            arch = ArchitectAgent(llm_client=llm)
            try:
                result = asyncio.run(arch.build_book(
                    name=name,
                    topic=topic,
                    genre=genre,
                    target_chapters=chapters,
                    words_per_chapter=words_per,
                    template=template,
                ))
                st.success(f"✅ 建书完成！项目已创建: `projects/{name}/`")
                st.page_link("pages/02_write.py", label="✍️ 去写稿 →")
            except Exception as e:
                st.error(f"建书失败: {e}")

st.page_link("studio.py", label="🏠 返回仪表盘")
