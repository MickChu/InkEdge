"""
向量索引 — Streamlit 页面

查看索引状态，语义搜索测试。
对应 CLI: python main.py index
"""
import sys, os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="向量索引 · InkEdge", page_icon="🔎")

projects_dir = PROJECT_ROOT / "projects"
names = [d.name for d in projects_dir.iterdir() if d.is_dir()] if projects_dir.exists() else []
proj_name = st.selectbox("选择项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    st.page_link("studio.py", label="🏠 返回仪表盘")
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
st.title(f"🔎 向量索引: {proj_name}")

chroma_dir = project_dir / "chroma_db"
has_index = chroma_dir.exists()

# ─── 索引状态 ───
st.subheader("📊 索引状态")

if has_index:
    try:
        from src.retrieval.vector_store import VectorStore
        vs = VectorStore(persist_dir=str(chroma_dir))

        collections = {
            "foundations": "基础设定",
            "chapters": "章节",
            "summaries": "摘要",
            "hooks": "伏笔",
        }

        cols = st.columns(4)
        for i, (col_name, label) in enumerate(collections.items()):
            try:
                count = vs.collection_count(col_name)
                with cols[i]:
                    st.metric(label, f"{count} 条")
            except Exception:
                with cols[i]:
                    st.metric(label, "—")
    except Exception as e:
        st.warning(f"索引状态读取失败: {e}")
else:
    st.info("尚未构建索引。CLI: `python main.py index -n '{proj_name}'`")
    if st.button("🔧 构建索引"):
        with st.spinner("正在构建索引..."):
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "main.py", "index", "-n", proj_name, "-f"],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )
                if result.returncode == 0:
                    st.success("✅ 索引构建完成")
                    st.rerun()
                else:
                    st.error(f"构建失败: {result.stderr}")
            except Exception as e:
                st.error(f"构建失败: {e}")

# ─── 语义搜索测试 ───
if has_index:
    st.divider()
    st.subheader("🔍 语义搜索测试")

    query = st.text_input("搜索关键词", placeholder="例: 破庙 记忆 秘密")
    if st.button("搜索") and query:
        try:
            from src.retrieval.vector_store import VectorStore
            vs = VectorStore(persist_dir=str(chroma_dir))
            results = vs.search(query, n_results=5)

            for i, (doc, meta, dist) in enumerate(zip(
                results.get("documents", [[]])[0],
                results.get("metadatas", [[]])[0],
                results.get("distances", [[]])[0],
            )):
                score = round(1 - min(dist, 1), 2)
                chapter = meta.get("chapter", "?")
                source = meta.get("source", "?")
                with st.container(border=True):
                    st.caption(f"**{i+1}.** 相似度: {score:.2f} · 来源: {source} · 第{chapter}章")
                    st.text(doc[:200] + ("..." if len(doc) > 200 else ""))
        except Exception as e:
            st.error(f"搜索失败: {e}")

    # 重建索引
    if st.button("🔧 强制重建索引"):
        with st.spinner("正在重建索引..."):
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "main.py", "index", "-n", proj_name, "-f"],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )
                if result.returncode == 0:
                    st.success("✅ 索引已重建")
                    st.rerun()
                else:
                    st.error(f"重建失败: {result.stderr}")
            except Exception as e:
                st.error(f"重建失败: {e}")

st.page_link("studio.py", label="🏠 返回仪表盘")
