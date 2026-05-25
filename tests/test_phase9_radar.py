"""
Phase 9 — 市场雷达测试（含协议层）
"""
import pytest
import sys
from pathlib import Path
PROJECT_ROOT = Path("H:/Python学习/AI写小说/InkEdge")
sys.path.insert(0, str(PROJECT_ROOT))


class TestRadarModels:
    def test_radar_entry_creation(self):
        from src.radar.base import RadarEntry
        e = RadarEntry(rank=1, title="测试", author="张三", genre="武侠", source="test")
        assert e.rank == 1 and e.tags == [] and e.source == "test"

    def test_genre_cluster_creation(self):
        from src.radar.base import GenreCluster
        c = GenreCluster(source="fanqie", uncovered=["游戏", "电竞"], suggested_new=["电竞"])
        assert c.source == "fanqie"
        assert "游戏" in c.uncovered
        assert "电竞" in c.suggested_new


class TestRadarSources:
    def test_fanqie_offline(self):
        from src.radar.sources import FanqieRadarSource
        r = FanqieRadarSource().offline_fallback()
        assert r.source == "fanqie" and "离线" in r.note

    def test_qidian_offline(self):
        from src.radar.sources import QidianRadarSource
        r = QidianRadarSource().offline_fallback()
        assert r.source == "qidian" and len(r.entries) > 0

    def test_knowledge_offline_filter(self):
        from src.radar.sources import KnowledgeRadarSource
        s = KnowledgeRadarSource()
        assert len(s.offline_fallback("科幻").entries) <= len(s.offline_fallback().entries)


class TestRadarAgent:
    def test_scan_no_sources(self):
        import asyncio
        from src.radar import RadarAgent
        r = asyncio.run(RadarAgent(sources=[]).scan(genre="武侠"))
        assert r.raw_entries_count >= 0 and len(r.sources) > 0

    def test_scan_with_knowledge(self):
        import asyncio
        from src.radar import RadarAgent
        from src.radar.sources import KnowledgeRadarSource
        r = asyncio.run(RadarAgent(sources=[KnowledgeRadarSource()]).scan(genre="科幻"))
        assert r.raw_entries_count > 0 and "knowledge" in r.sources

    def test_identify_trends(self):
        import asyncio
        from src.radar import RadarAgent
        from src.radar.sources import KnowledgeRadarSource
        trends = asyncio.run(
            RadarAgent(sources=[KnowledgeRadarSource()]).identify_trends()
        )
        assert "rising" in trends and "declining" in trends and "stable" in trends
        assert "summary" in trends

    def test_cluster_genres_rule_based(self):
        import asyncio
        from src.radar import RadarAgent
        cluster = asyncio.run(RadarAgent().cluster_genres(source="fanqie"))
        assert cluster.source == "fanqie"
        assert len(cluster.clusters) > 8
        # 玄幻应归入奇幻
        xuanhuan = [c for c in cluster.clusters if c["platform_category"] == "玄幻"]
        assert xuanhuan
        assert xuanhuan[0]["mapped_to"] == "奇幻"

    def test_cluster_genres_all(self):
        import asyncio
        from src.radar import RadarAgent
        cluster = asyncio.run(RadarAgent().cluster_genres(source="all"))
        assert len(cluster.clusters) > 15

    def test_parse_scan_response(self):
        from src.radar import RadarAgent, TrendReport
        agent = RadarAgent()
        base = TrendReport(genre="武侠")
        content = "=== TREND_SUMMARY ===\n武侠火热\n=== HOT_TAGS ===\n- 修炼\n=== TREND_INSIGHTS ===\n- 国风\n=== WRITING_ADVICE ===\n- 穿越"
        r = agent._parse_scan(content, base)
        assert "火热" in r.summary and "修炼" in r.hot_tags

    def test_parse_trends_response(self):
        from src.radar import RadarAgent
        agent = RadarAgent()
        content = (
            "=== SUMMARY ===\n末世上升\n"
            "=== RISING ===\n- 末世 | 0.9 | 多本爆款\n"
            "=== DECLINING ===\n- 传统修真 | 0.7 | 同质化\n"
            "=== STABLE ===\n- 都市 | 0.8 | 大盘稳定\n"
        )
        r = agent._parse_trends(content)
        assert len(r["rising"]) == 1 and r["rising"][0]["category"] == "末世"
        assert len(r["declining"]) == 1 and r["stable"]

    def test_parse_cluster_response(self):
        from src.radar import RadarAgent, GenreCluster
        agent = RadarAgent()
        base = GenreCluster(source="fanqie")
        content = (
            "=== MAPPING ===\n"
            "- 玄幻 → 奇幻 | 0.85\n"
            "- 游戏 → 科幻 | 0.65\n"
            "=== UNCOVERED ===\n"
            "- 电竞\n"
            "=== SUGGESTED_NEW ===\n"
            "- 电竞 | 市场体量大\n"
        )
        r = agent._parse_cluster(content, base)
        assert len(r.clusters) == 2
        assert "电竞" in r.uncovered
        assert len(r.suggested_new) == 1

    def test_category_lists(self):
        from src.radar import RadarAgent
        fanqie = RadarAgent._fanqie_categories()
        qidian = RadarAgent._qidian_categories()
        assert "仙侠" in fanqie and "玄幻" in qidian
        assert len(fanqie) >= 10
        assert len(qidian) >= 14

    def test_current_genre_list(self):
        from src.radar import RadarAgent
        genres = RadarAgent._current_genre_list()
        assert len(genres) == 6
        keys = [g[0] for g in genres]
        assert "wuxia" in keys and "scifi" in keys


class TestGenreKnowledgeBuilder:
    def test_builder_instantiable(self):
        from src.radar import GenreKnowledgeBuilderStub
        builder = GenreKnowledgeBuilderStub()
        assert builder is not None

    def test_from_radar_data_returns_draft(self):
        import asyncio
        from src.radar import GenreKnowledgeBuilderStub
        builder = GenreKnowledgeBuilderStub()
        draft = asyncio.run(builder.from_radar_data(
            trends={"summary": "末世文上升"}, genre="apocalypse",
        ))
        assert draft["genre"] == "apocalypse"
        assert draft["needs_review"] is True
        assert "draft_path" in draft
        for field in ["injection_text", "naming_conventions", "hierarchy_systems",
                       "character_archetypes", "plot_patterns"]:
            assert field in draft

    def test_validate_module(self):
        from src.radar import GenreKnowledgeBuilderStub
        builder = GenreKnowledgeBuilderStub()
        draft = {
            "genre": "test", "injection_text": "x" * 100,
            "naming_conventions": "x" * 10,
            "hierarchy_systems": "x" * 80,
            "character_archetypes": "x" * 60,
            "plot_patterns": "x" * 20,
        }
        checks = builder.validate_module(draft)
        assert len(checks) == 5
        passed = [c for c in checks if c["passed"]]
        failed = [c for c in checks if not c["passed"]]
        assert len(passed) == 3  # 100, 80, 60 >= 50
        assert len(failed) == 2  # 10, 20 < 50


class TestProtocols:
    def test_radar_agent_satisfies_analyzer(self):
        from src.radar.base import RadarAnalyzer
        from src.radar import RadarAgent
        agent = RadarAgent()
        assert isinstance(agent, RadarAnalyzer)

    def test_builder_satisfies_protocol(self):
        from src.radar.base import GenreKnowledgeBuilder
        from src.radar import GenreKnowledgeBuilderStub
        builder = GenreKnowledgeBuilderStub()
        assert isinstance(builder, GenreKnowledgeBuilder)
