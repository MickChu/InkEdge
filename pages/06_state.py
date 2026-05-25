"""
角色状态 — Streamlit 页面

Phase 6 角色状态追踪: 物品/能力/关系图
Phase 11 结算系统: 情感弧线/角色交互矩阵/伏笔池/支线面板
对应 CLI: python main.py state + python main.py settle
"""
import sys, os, json
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title="角色状态 · InkEdge", page_icon="⚔️", layout="wide")

projects_dir = PROJECT_ROOT / "projects"
names = [d.name for d in projects_dir.iterdir() if d.is_dir()] if projects_dir.exists() else []
proj_name = st.selectbox("选择项目", names) if names else st.text_input("项目名")

if not proj_name:
    st.info("请选择一个项目")
    st.page_link("studio.py", label="🏠 返回仪表盘")
    st.stop()

project_dir = PROJECT_ROOT / "projects" / proj_name
st.title(f"⚔️ 角色状态: {proj_name}")

state_dir = project_dir / "story" / "state"

# ─── Tab切换: Phase6 角色状态 + Phase11 结算系统 ───
tab_char, tab_settle = st.tabs(["⚔️ 角色状态 (P6)", "📊 结算面板 (P11)"])

# ═══════════════════════════════════════════════
# Tab 1: Phase 6 角色状态
# ═══════════════════════════════════════════════
with tab_char:
    state_file = project_dir / "character_state.json"
    has_state = state_file.exists()

    if not has_state:
        st.info("尚无角色状态数据。写一章后会自动追踪。")
    else:
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            chars = state.get("characters", {})

            if not chars:
                st.info("角色状态文件存在但为空")
            else:
                cols = st.columns(min(len(chars), 3))
                for i, (name, data) in enumerate(chars.items()):
                    with cols[i % 3]:
                        with st.container(border=True):
                            tag = "⭐" if data.get("is_protagonist") else "👤"
                            st.subheader(f"{tag} {name}")

                            # 物品
                            inv = data.get("inventory", [])
                            if inv:
                                st.caption("📦 物品")
                                for item in inv:
                                    st.write(f"· {item['name']} × {item.get('quantity', 1)}")
                            else:
                                st.caption("📦 物品: —")

                            # 能力
                            abi = data.get("abilities", [])
                            if abi:
                                st.caption("⚡ 能力")
                                for a in abi:
                                    lv = a.get('level', '')
                                    lv_str = f"({lv})" if lv else ""
                                    st.write(f"· {a['name']}{lv_str}")
                            else:
                                st.caption("⚡ 能力: —")

                            # 位置/状态
                            loc = data.get("location", "")
                            phys = data.get("physical_state", "")
                            if loc or phys:
                                st.caption("📍 状态")
                                if loc:
                                    st.write(f"位置: {loc}")
                                if phys:
                                    st.write(f"身体: {phys}")

                            # 关系
                            rels = data.get("relationships", {})
                            if rels:
                                st.caption("👥 关系")
                                for target, rel_data in rels.items():
                                    trust = rel_data.get("trust", 0)
                                    desc = rel_data.get("description", "")
                                    st.write(f"→ {target}: {desc} (信任:{trust})")

            # 快照
            snap_dir = project_dir / "state" / "snapshots"
            snaps = list(snap_dir.glob("*.json")) if snap_dir.exists() else []
            # 也检查旧格式
            snap_dir2 = project_dir / "state" / "snapshots" if (project_dir / "state").exists() else None

        except Exception as e:
            st.error(f"加载角色状态失败: {e}")

    # 手动触发追踪
    with st.expander("🔄 手动更新"):
        ch_dir = project_dir / "chapters"
        existing = sorted([int(f.stem) for f in ch_dir.glob("*.md")]) if ch_dir.exists() else []
        if existing:
            ch = st.selectbox("对哪一章更新状态", existing, key="state_ch")
            if st.button("🔍 更新角色状态"):
                ch_file = ch_dir / f"{ch:04d}.md"
                text = ch_file.read_text(encoding="utf-8")
                try:
                    from src.state.manager import StateManager
                    mgr = StateManager(str(project_dir))
                    mgr.track_characters_sync(text, ch)
                    st.success(f"✅ 第{ch}章角色状态已更新")
                    st.rerun()
                except Exception as e:
                    st.error(f"更新失败: {e}")

# ═══════════════════════════════════════════════
# Tab 2: Phase 11 结算面板
# ═══════════════════════════════════════════════
with tab_settle:
    st.caption("Observer + 3 Settlers 写后结算: 状态卡 · 情感弧线 · 角色矩阵 · 伏笔池 · 支线面板")

    files_map = {
        "🌍 状态卡": "current_state.md",
        "💎 资源账本": "ledger.md",
        "❤️ 情感弧线": "emotional_arcs.md",
        "🔗 角色交互矩阵": "character_matrix.md",
        "🎯 伏笔池": "hooks.md",
        "📋 支线面板": "subplots.md",
    }

    if not state_dir.exists():
        st.info("尚未结算。写一章后运行 `python main.py settle`。")
    else:
        for label, filename in files_map.items():
            fp = state_dir / filename
            if fp.exists():
                with st.expander(f"{label} — {filename}", expanded=(label == "🌍 状态卡")):
                    content = fp.read_text(encoding="utf-8")
                    st.markdown(content[:5000])
            else:
                st.caption(f"{label}: 尚未生成")

        # 手动触发结算
        st.divider()
        ch_dir = project_dir / "chapters"
        existing = sorted([int(f.stem) for f in ch_dir.glob("*.md")]) if ch_dir.exists() else []
        if existing:
            ch_settle = st.selectbox("对哪一章运行结算", existing, key="settle_ch")
            if st.button("🔄 运行结算", key="btn_settle"):
                with st.spinner("结算中（Observer → 3 Settlers 并行）..."):
                    try:
                        import asyncio
                        from src.core.llm_client import LLMClient
                        from src.settlement import SettlementOrchestrator

                        ch_file = ch_dir / f"{ch_settle:04d}.md"
                        ch_text = ch_file.read_text(encoding="utf-8")

                        llm = LLMClient()
                        orch = SettlementOrchestrator(str(project_dir))
                        report = asyncio.run(orch.settle(
                            ch_text, ch_settle, llm,
                            chapter_count=len(existing),
                        ))

                        st.success(report.summary())
                        st.rerun()
                    except Exception as e:
                        st.error(f"结算失败: {e}")
                        st.exception(e)

st.page_link("studio.py", label="🏠 返回仪表盘")
