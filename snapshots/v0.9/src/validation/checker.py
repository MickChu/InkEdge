"""
Phase 5 — CheckOrchestrator（校验编排器）

协调三个校验器并行运行，生成综合报告。
"""
import logging
from typing import Optional

from .report import CheckReport, DuplicationReport, AIStyleReport, ConsistencyReport
from .duplication import DuplicationChecker
from .ai_style import AIStyleScorer
from .consistency import ConsistencyValidator

log = logging.getLogger(__name__)


class CheckOrchestrator:
    """后验校验编排器"""

    def __init__(self, project_dir: str,
                 sim_threshold: float = 0.15,
                 skip_duplication: bool = False,
                 skip_ai_style: bool = False,
                 skip_consistency: bool = False):
        self.project_dir = project_dir
        self.skip_duplication = skip_duplication
        self.skip_ai_style = skip_ai_style
        self.skip_consistency = skip_consistency
        self.dup_checker = DuplicationChecker(threshold=sim_threshold)
        self.style_scorer = AIStyleScorer()
        self.consistency_validator = ConsistencyValidator(project_dir)

    def run(self, chapter_text: str, chapter_number: int,
            project_name: str, store=None) -> CheckReport:
        """
        运行全部校验。

        Args:
            chapter_text: 章节全文
            chapter_number: 章节号
            project_name: 项目名
            store: VectorStore 实例（重复检测需要）

        Returns:
            CheckReport
        """
        word_count = len(chapter_text)
        report = CheckReport(
            project_name=project_name,
            chapter_number=chapter_number,
            word_count=word_count,
        )

        # 1. 重复检测（需要 VectorStore）
        if not self.skip_duplication and store is not None:
            try:
                report.duplication = self.dup_checker.check(
                    chapter_text, store, skip_chapter=chapter_number
                )
            except Exception as e:
                log.warning(f"重复检测失败: {e}")
                report.duplication = DuplicationReport(
                    passed=True,
                    summary=f"检测失败: {e}",
                )
        elif self.skip_duplication:
            report.duplication = DuplicationReport(
                passed=True,
                summary="已跳过（--skip-duplication）",
            )
        else:
            report.duplication = DuplicationReport(
                passed=True,
                summary="无索引可用（需先运行 index）",
            )

        # 2. AI 痕迹评分
        if not self.skip_ai_style:
            try:
                report.ai_style = self.style_scorer.score(chapter_text)
            except Exception as e:
                log.warning(f"AI痕迹评分失败: {e}")
                report.ai_style = AIStyleReport(score=0, level="未知")

        # 3. 一致性校验
        if not self.skip_consistency:
            try:
                report.consistency = self.consistency_validator.validate(
                    chapter_text, chapter_number,
                )
            except Exception as e:
                log.warning(f"一致性校验失败: {e}")
                report.consistency = ConsistencyReport(passed=True)

        return report
