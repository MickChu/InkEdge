"""
Phase 9 — 市场雷达
扫描实时排行榜，LLM 分析趋势，产出开书建议。
"""
from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod

@dataclass
class RadarEntry:
    rank: int
    title: str
    author: str = ""
    genre: str = ""
    popularity: int = 0
    word_count: str = ""
    status: str = ""
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    source: str = ""

@dataclass
class RadarReport:
    source: str
    entries: List[RadarEntry] = field(default_factory=list)
    fetched_at: str = ""
    note: str = ""

@dataclass
class TrendReport:
    genre: str = ""
    summary: str = ""
    hot_tags: List[str] = field(default_factory=list)
    trend_insights: str = ""
    writing_advice: str = ""
    raw_entries_count: int = 0
    sources: List[str] = field(default_factory=list)

class RadarSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    async def fetch(self, genre: str = "", limit: int = 30) -> RadarReport: ...
    def offline_fallback(self, genre: str = "", limit: int = 30) -> RadarReport:
        return RadarReport(source=self.name, note="离线无数据")


# ── 协议层 ──────────────────────────────────────────────

@dataclass
class GenreCluster:
    """平台分类 → 创作品类的归并建议"""
    source: str                                    # 平台名 (fanqie/qidian)
    clusters: List[dict] = field(default_factory=list)  # [{name, genres, mapped_to, confidence}]
    uncovered: List[str] = field(default_factory=list)  # 当前6类覆盖不到的分类
    suggested_new: List[str] = field(default_factory=list)  # 建议新建模块的分类


class RadarAnalyzer(ABC):
    """市场雷达分析器协议 — 可按需扩展"""

    @abstractmethod
    async def scan(self, genre: str = "", limit: int = 30, llm_client=None) -> TrendReport:
        """扫描排行榜 + 趋势分析"""

    @abstractmethod
    async def identify_trends(self, genre: str = "", limit: int = 30, llm_client=None) -> dict:
        """
        识别市场上升/下降品类。

        Returns:
            {
                "rising": [{"category": "末世", "confidence": 0.9, "evidence": "..."}, ...],
                "declining": [...],
                "stable": [...],
                "summary": "一句话趋势总结"
            }
        """

    @abstractmethod
    async def cluster_genres(self, source: str = "all", llm_client=None) -> GenreCluster:
        """
        分析平台的原始分类体系，给出归并建议。

        Args:
            source: 平台名 (fanqie/qidian/all)

        Returns:
            GenreCluster: 归并方案 + 未覆盖项 + 建议新建项
        """


class GenreKnowledgeBuilder(ABC):
    """类型知识自动生成器协议 — 预留日后扩展"""

    @abstractmethod
    async def from_radar_data(self, trends: dict, genre: str, llm_client=None) -> dict:
        """
        从雷达趋势数据自动生成类型知识模块草稿。

        Args:
            trends: identify_trends() 的输出
            genre: 目标品类名

        Returns:
            {
                "genre": str,
                "display_name": str,
                "injection_text": str,        # 写作惯例
                "naming_conventions": str,    # 命名体系
                "hierarchy_systems": str,     # 等级/战力体系
                "character_archetypes": str,  # 角色原型
                "plot_patterns": str,         # 情节模式
                "draft_path": str,            # 建议保存路径
                "needs_review": bool,         # 需人工审核
            }
        """

    @abstractmethod
    def validate_module(self, draft: dict) -> list:
        """
        验证自动生成的模块质量。

        Returns:
            [{"check": "命名体系完整性", "passed": True/False, "note": "..."}, ...]
        """
