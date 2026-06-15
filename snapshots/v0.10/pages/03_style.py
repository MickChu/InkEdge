"""
风格管理 — Streamlit 页面

上传作家片段，分析并生成风格指南。
对应 CLI: python main.py style
"""
import sys, os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="风格管理 · InkEdge", page_icon="🎨")

# ─── 项目选择 ───
projects_dir = PROJECT_ROOT / "projects"
names = [d.name for d in projects_dir.iterdir() if d.is_dir()] if projects_dir.exists() else []
proj_name = st.selectbox("选择项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    floating_home()
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
st.title(f"🎨 风格管理: {proj_name}")

# ─── 当前风格指南 ───
style_guide_path = project_dir / "style_guide.md"
if style_guide_path.exists():
    with st.expander("📖 当前风格指南", expanded=True):
        content = style_guide_path.read_text(encoding="utf-8")
        st.markdown(content[:4000])
        if len(content) > 4000:
            st.caption(f"... (共 {len(content)} 字)")
else:
    st.info("尚未生成风格指南。上传作家文本来创建。")

# ─── 更新风格 ───
st.divider()
st.subheader("🔄 更新风格指南")

tab_file, tab_text = st.tabs(["📁 上传文件", "📝 粘贴文本"])

with tab_file:
    uploaded = st.file_uploader("上传作家片段 (.txt, .md)", type=["txt", "md"])
    if uploaded:
        text = uploaded.read().decode("utf-8")
        st.text_area("预览", text[:1000], height=150, disabled=True)
        if st.button("🎨 分析风格 (文件)", type="primary"):
            with st.spinner("正在分析风格..."):
                try:
                    import asyncio
                    from src.core.llm_client import LLMClient
                    from src.governance.style.analyzer import StyleAnalyzer
                    llm = LLMClient()
                    analyzer = StyleAnalyzer(llm_client=llm, project_dir=str(project_dir))
                    result = asyncio.run(analyzer.analyze(text))
                    style_guide_path.parent.mkdir(parents=True, exist_ok=True)
                    style_guide_path.write_text(result, encoding="utf-8")
                    st.success("✅ 风格指南已更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"分析失败: {e}")

with tab_text:
    text_input = st.text_area("粘贴作家文本", height=200,
                              placeholder="粘贴想要模仿的作家作品片段...")
    if st.button("🎨 分析风格 (文本)", type="primary", disabled=not text_input):
        with st.spinner("正在分析风格..."):
            try:
                import asyncio
                from src.core.llm_client import LLMClient
                from src.governance.style.analyzer import StyleAnalyzer
                llm = LLMClient()
                analyzer = StyleAnalyzer(llm_client=llm, project_dir=str(project_dir))
                result = asyncio.run(analyzer.analyze(text_input))
                style_guide_path.parent.mkdir(parents=True, exist_ok=True)
                style_guide_path.write_text(result, encoding="utf-8")
                st.success("✅ 风格指南已更新！")
                st.rerun()
            except Exception as e:
                st.error(f"分析失败: {e}")

floating_home()
