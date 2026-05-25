"""
校验报告 — Streamlit 页面

Phase 5 后验校验: 重复检测 + AI痕迹 + 一致性
对应 CLI: python main.py check
"""
import sys, os
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="校验 · InkEdge", page_icon="🔍")

projects_dir = PROJECT_ROOT / "projects"
names = [d.name for d in projects_dir.iterdir() if d.is_dir()] if projects_dir.exists() else []
proj_name = st.selectbox("选择项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    st.page_link("studio.py", label="🏠 返回仪表盘")
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
st.title(f"🔍 校验报告: {proj_name}")

# ─── 章节选择 ───
ch_dir = project_dir / "chapters"
existing = sorted([int(f.stem) for f in ch_dir.glob("*.md")]) if ch_dir.exists() else []
if not existing:
    st.info("还没有章节。先去写一章吧。")
    st.page_link("pages/02_write.py", label="✍️ 去写稿")
    st.stop()

chapter = st.selectbox("选择章节", existing, index=len(existing) - 1)

# ─── 校验选项 ───
col1, col2, col3 = st.columns(3)
with col1:
    run_dup = st.checkbox("重复检测", value=True)
with col2:
    run_ai = st.checkbox("AI痕迹评估", value=True)
with col3:
    run_con = st.checkbox("一致性校验", value=True)

if st.button("🔍 开始校验", type="primary", use_container_width=True):
    ch_file = ch_dir / f"{chapter:04d}.md"
    ch_text = ch_file.read_text(encoding="utf-8")

    with st.spinner("校验中..."):
        try:
            import asyncio
            from src.validation.checker import CheckOrchestrator
            orch = CheckOrchestrator(str(project_dir))
            report = asyncio.run(orch.check(
                chapter_text=ch_text,
                chapter_number=chapter,
                skip_duplication=not run_dup,
                skip_ai_style=not run_ai,
                skip_consistency=not run_con,
            ))

            # ─── 重复检测 ───
            if run_dup:
                st.subheader("📋 重复检测")
                dup = report.get("duplication", {})
                if dup.get("matches"):
                    st.warning(f"发现 {len(dup['matches'])} 处疑似重复")
                    for m in dup["matches"][:5]:
                        with st.expander(f"相似度 {m.get('score', 0):.2f} · {m.get('source', '?')}"):
                            st.text(m.get("text", "")[:300])
                else:
                    st.success("✅ 未发现重复内容")

            # ─── AI痕迹 ───
            if run_ai:
                st.subheader("🤖 AI痕迹评估")
                ai = report.get("ai_style", {})
                score = ai.get("score", 0)
                st.metric("AI痕迹评分", f"{score}/100",
                          delta="低" if score < 30 else ("中" if score < 60 else "高"),
                          delta_color="normal" if score < 30 else ("off" if score < 60 else "inverse"))

                if ai.get("findings"):
                    for f in ai["findings"]:
                        st.markdown(f"- {f}")

            # ─── 一致性 ───
            if run_con:
                st.subheader("🔗 一致性校验")
                con = report.get("consistency", {})
                if con.get("issues"):
                    st.warning(f"发现 {len(con['issues'])} 个问题")
                    for issue in con["issues"]:
                        st.markdown(f"- ⚠️ {issue}")
                else:
                    st.success("✅ 未发现一致性问题")

        except Exception as e:
            st.error(f"校验失败: {e}")
            st.exception(e)

st.page_link("studio.py", label="🏠 返回仪表盘")
