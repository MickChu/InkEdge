"""
Phase 5 — 后验校验系统

三校验器并行架构：
  - DuplicationChecker    — 语义重复检测
  - AIStyleScorer         — AI 痕迹评分
  - ConsistencyValidator  — 一致性校验

使用方式:
  from src.validation import check_project
  report = check_project("书", 10, "projects/书/chapter_0010.md")
  print(report.format_cli())
"""
from .report import CheckReport, DuplicationReport, AIStyleReport, ConsistencyReport
from .duplication import DuplicationChecker
from .ai_style import AIStyleScorer
from .consistency import ConsistencyValidator
from .checker import CheckOrchestrator

__all__ = [
    "CheckReport",
    "DuplicationReport",
    "AIStyleReport",
    "ConsistencyReport",
    "DuplicationChecker",
    "AIStyleScorer",
    "ConsistencyValidator",
    "CheckOrchestrator",
]
