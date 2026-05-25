"""
Phase 9 — 市场雷达 (Market Radar)

协议:
  RadarAnalyzer      — 分析器接口 (scan / identify_trends / cluster_genres)
  GenreKnowledgeBuilder — 类型知识自动生成器接口 (from_radar_data / validate_module)

使用:
  from src.radar import RadarAgent, GenreCluster
  agent = RadarAgent(sources=[KnowledgeRadarSource()])
  report = await agent.scan(genre="武侠", llm_client=llm)
  trends = await agent.identify_trends(llm_client=llm)
  cluster = await agent.cluster_genres(source="all", llm_client=llm)

CLI:
  python main.py radar scan --genre 武侠
  python main.py radar trends
  python main.py radar cluster --source fanqie
"""
from .base import (
    RadarSource, RadarEntry, RadarReport, TrendReport,
    GenreCluster, RadarAnalyzer, GenreKnowledgeBuilder,
)
from .sources import FanqieRadarSource, QidianRadarSource, KnowledgeRadarSource
from .agent import RadarAgent, GenreKnowledgeBuilderStub

__all__ = [
    # 数据模型
    "RadarSource", "RadarEntry", "RadarReport", "TrendReport",
    "GenreCluster",
    # 协议
    "RadarAnalyzer", "GenreKnowledgeBuilder",
    # 实现
    "FanqieRadarSource", "QidianRadarSource", "KnowledgeRadarSource",
    "RadarAgent", "GenreKnowledgeBuilderStub",
]
