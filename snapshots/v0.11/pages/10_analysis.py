"""
写作分析 — Streamlit 页面

密度分析 / 伏笔追踪 / 冲突曲线
对应 CLI: python main.py analyze
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.utils.ui_helpers import floating_home

st.set_page_config(page_title="写作分析 · InkEdge", page_icon="📊", layout="wide")
floating_home()

# ─── 选择项目 ───
projects_dir = PROJECT_ROOT / "projects"
if projects_dir.exists():
    names = [d.name for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
else:
    names = []
proj_name = st.selectbox("项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
if not project_dir.exists():
    st.error(f"项目不存在: {proj_name}")
    st.stop()

st.title(f"📊 写作分析: {proj_name}")

# ─── 分析模式 ───
mode = st.radio("分析类型", ["密度分析", "伏笔追踪", "冲突曲线", "全部"], horizontal=True)

st.divider()

# ============================================================
# 密度分析
# ============================================================
if mode in ("密度分析", "全部"):
    st.subheader("📊 密度分析")

    col1, col2 = st.columns([3, 1])
    with col1:
        show_fill = st.checkbox("💧 灌水模式——标出密度偏低的章节，给出扩展建议")
    with col2:
        fill_target = st.selectbox("灌水目标", ["description", "dialogue", "action", "inner"],
                                   format_func=lambda x: {"description": "描写", "dialogue": "对话", "action": "动作", "inner": "内心"}[x])

    from src.analysis import DensityAnalyzer
    da = DensityAnalyzer(str(project_dir))

    if show_fill:
        report = da.analyze_fill(target_density=fill_target)
    else:
        report = da.analyze()

    if report.stats:
        # 密度表格
        st.write(f"共 {len(report.stats)} 章")
        data = [s.to_dict() for s in report.stats]
        st.dataframe(data, use_container_width=True, hide_index=True,
                     column_config={
                         "chapter": "章节",
                         "total_chars": "字数",
                         "dialogue_pct": st.column_config.ProgressColumn("对话%", min_value=0, max_value=100, format="%.0f%%"),
                         "action_pct": st.column_config.ProgressColumn("动作%", min_value=0, max_value=100, format="%.0f%%"),
                         "description_pct": st.column_config.ProgressColumn("描写%", min_value=0, max_value=100, format="%.0f%%"),
                         "inner_pct": st.column_config.ProgressColumn("内心%", min_value=0, max_value=100, format="%.0f%%"),
                     })

        # 警告
        if report.warnings:
            with st.expander(f"⚠️ 节奏警告 ({len(report.warnings)} 条)", expanded=True):
                for w in report.warnings:
                    st.warning(w)

        # 灌水建议
        if report.fill_suggestions:
            with st.expander(f"💧 灌水建议 ({len(report.fill_suggestions)} 条)", expanded=True):
                for f in report.fill_suggestions:
                    st.info(f)
    else:
        st.info("无章节数据")

st.divider()

# ============================================================
# 伏笔追踪
# ============================================================
if mode in ("伏笔追踪", "全部"):
    st.subheader("🎯 伏笔追踪")

    from src.analysis import ForeshadowTracker
    ft = ForeshadowTracker(str(project_dir))
    rpt = ft.report()

    col1, col2, col3 = st.columns(3)
    col1.metric("总计", rpt.total)
    col2.metric("已回收", len(rpt.resolved),
                delta=f"-{len(rpt.resolved)}" if rpt.total > 0 else None,
                delta_color="off")
    col3.metric("逾期未提醒", len(rpt.overdue),
                delta_color="inverse")

    if rpt.pending:
        with st.expander(f"⏳ 待回收 ({len(rpt.pending)})", expanded=True):
            for h in rpt.pending:
                st.text(f"{h.id}: {h.description[:80]}")

    if rpt.overdue:
        with st.expander(f"⚠️ 逾期 (>20章未提醒) ({len(rpt.overdue)})", expanded=True):
            for h in rpt.overdue:
                st.error(f"{h.id} (第{h.planted_chapter}章埋设): {h.description[:80]}")

    if rpt.resolved:
        with st.expander(f"✅ 已回收 ({len(rpt.resolved)})"):
            for h in rpt.resolved:
                st.success(f"{h.id} → 第{h.resolved_chapter}章回收: {h.resolution[:60] or h.description[:60]}")

    # 迁移按钮
    md_path = project_dir / "pending_hooks.md"
    if md_path.exists():
        if st.button("📥 从 pending_hooks.md 迁移", help="将旧的文本格式伏笔迁移为结构化 JSON"):
            count = ft.migrate_from_md()
            st.success(f"已迁移 {count} 条伏笔")
            st.rerun()

st.divider()

# ============================================================
# 冲突曲线
# ============================================================
if mode in ("冲突曲线", "全部"):
    st.subheader("⚔️ 冲突曲线")

    from src.analysis import ConflictTracker
    ct = ConflictTracker(str(project_dir))
    report = ct.analyze()

    if report.stats:
        # 强度曲线图
        import pandas as pd
        df = pd.DataFrame([s.to_dict() for s in report.stats])
        st.line_chart(df, x="chapter", y=["intensity"], height=300)

        # 平均值
        avg_intensity = sum(s.intensity for s in report.stats) / len(report.stats)
        dominants = {}
        for s in report.stats:
            d = s.dominant
            dominants[d] = dominants.get(d, 0) + 1

        col1, col2, col3 = st.columns(3)
        col1.metric("平均强度", f"{avg_intensity:.1f}/10")
        for dtype, count in sorted(dominants.items(), key=lambda x: -x[1]):
            col2.metric(f"主导: {dtype}", f"{count} 章")

        # 警告
        for w in report.warnings:
            st.warning(w)

        # 详细数据
        with st.expander("📋 详细数据"):
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("无章节数据")
