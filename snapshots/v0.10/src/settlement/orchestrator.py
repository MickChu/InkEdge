"""
Phase 11 — SettlementOrchestrator: 结算编排器

协调 Observer → 3 Settlers 的完整流水线：
1. Observer 提取所有事实
2. WorldSettler / CharacterSettler / PlotSettler 并行结算
3. 汇总输出
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from .observer import Observer
from .world_settler import WorldSettler, WorldSettleOutput
from .character_settler import CharacterSettler, CharacterSettleOutput
from .plot_settler import PlotSettler, PlotSettleOutput

log = logging.getLogger(__name__)


@dataclass
class SettlementReport:
    """结算汇总报告"""
    chapter_number: int = 0
    observations: str = ""
    world: Optional[WorldSettleOutput] = None
    character: Optional[CharacterSettleOutput] = None
    plot: Optional[PlotSettleOutput] = None

    def summary(self) -> str:
        lines = [
            f"📊 结算报告: 第{self.chapter_number}章",
            "",
        ]
        if self.world:
            lines.append(f"🌍 世界观: {'✅' if self.world.updated_state else '⚠️'}")
        if self.character:
            lines.append(f"👤 角色:   {'✅' if self.character.updated_emotional_arcs else '⚠️'}")
        if self.plot:
            lines.append(f"📖 情节:   {'✅' if self.plot.updated_hooks else '⚠️'}")
        return "\n".join(lines)


class SettlementOrchestrator:
    """结算编排器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.observer = Observer()
        self.world = WorldSettler(project_dir)
        self.character = CharacterSettler(project_dir)
        self.plot = PlotSettler(project_dir)

    async def settle(self, chapter_text: str, chapter_number: int,
                     llm_client, chapter_count: int = 0,
                     volume_outline: str = "") -> SettlementReport:
        """
        完整结算流水线。

        Args:
            chapter_text: 章节全文
            chapter_number: 章号
            llm_client: LLM 客户端
            chapter_count: 已写章数
            volume_outline: 卷纲参考

        Returns:
            SettlementReport
        """
        report = SettlementReport(chapter_number=chapter_number)

        # 1. Observer — 提取事实
        observations = await self.observer.observe(
            chapter_text, chapter_number, llm_client,
        )
        report.observations = observations
        log.info(f"[Settlement] Observer 完成 ({len(observations)} 字符)")

        # 2. 三个 Settler 并行结算
        world_task = self.world.settle(chapter_number, observations, llm_client)
        char_task = self.character.settle(
            chapter_number, observations, llm_client, volume_outline,
        )
        plot_task = self.plot.settle(
            chapter_number, observations, llm_client, chapter_count, volume_outline,
        )

        results = await asyncio.gather(world_task, char_task, plot_task,
                                       return_exceptions=True)

        report.world = results[0] if not isinstance(results[0], Exception) else None
        report.character = results[1] if not isinstance(results[1], Exception) else None
        report.plot = results[2] if not isinstance(results[2], Exception) else None

        if isinstance(results[0], Exception):
            log.warning(f"[WorldSettler] 异常: {results[0]}")
        if isinstance(results[1], Exception):
            log.warning(f"[CharacterSettler] 异常: {results[1]}")
        if isinstance(results[2], Exception):
            log.warning(f"[PlotSettler] 异常: {results[2]}")

        log.info(f"[Settlement] 第{chapter_number}章结算完成")
        return report

    def settle_sync(self, chapter_text: str, chapter_number: int
                    ) -> SettlementReport:
        """
        同步结算（正则回退版，不需要 LLM）。
        Observer 用正则提取，Settler 不执行（没有 LLM 无法结算）。
        """
        report = SettlementReport(chapter_number=chapter_number)
        report.observations = self.observer.observe_sync(
            chapter_text, chapter_number,
        )
        log.info(f"[Settlement] 同步观察完成 ({len(report.observations)} 字符)")
        return report
