"""
Phase 11 — 结算系统 (Settlement)

移植自 inkOS 的 Observer + 3 Settlers 架构：
  写后 → Observer(提取事实) → 3 Settlers(并行结算)

Settler 分工：
  - WorldSettler      → 状态卡 + 资源账本
  - CharacterSettler  → 情感弧线 + 角色交互矩阵
  - PlotSettler       → 伏笔池 + 章节摘要 + 支线面板

使用方式:
  from src.settlement import SettlementOrchestrator
  orch = SettlementOrchestrator(project_dir)
  report = await orch.settle(chapter_text, chapter_number, llm_client)
"""
from .observer import Observer
from .world_settler import WorldSettler, WorldSettleOutput
from .character_settler import CharacterSettler, CharacterSettleOutput
from .plot_settler import PlotSettler, PlotSettleOutput
from .orchestrator import SettlementOrchestrator, SettlementReport

__all__ = [
    "Observer",
    "WorldSettler",
    "CharacterSettler",
    "PlotSettler",
    "SettlementOrchestrator",
    "SettlementReport",
    "WorldSettleOutput",
    "CharacterSettleOutput",
    "PlotSettleOutput",
]
