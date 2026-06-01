"""
Phase 8 — 类型知识注入系统测试

测试 KnowledgeLoader、GenreKnowledge、Architect/ContextBuilder 集成。
"""
import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path("H:/Python学习/AI写小说/InkEdge")
sys.path.insert(0, str(PROJECT_ROOT))


class TestGenreKnowledge:
    """GenreKnowledge 数据类测试"""

    def test_wuxia_knowledge_loaded(self):
        from src.genre_knowledge.genres.wuxia import WUXIA_KNOWLEDGE
        assert WUXIA_KNOWLEDGE.genre == "wuxia"
        assert "武侠" in WUXIA_KNOWLEDGE.display_name
        assert len(WUXIA_KNOWLEDGE.injection_text) > 50
        assert len(WUXIA_KNOWLEDGE.naming_conventions) > 20

    def test_scifi_knowledge_loaded(self):
        from src.genre_knowledge.genres.scifi import SCIFI_KNOWLEDGE
        assert SCIFI_KNOWLEDGE.genre == "scifi"
        assert "科幻" in SCIFI_KNOWLEDGE.display_name
        assert len(SCIFI_KNOWLEDGE.injection_text) > 50

    def test_urban_knowledge_loaded(self):
        from src.genre_knowledge.genres.urban import URBAN_KNOWLEDGE
        assert URBAN_KNOWLEDGE.genre == "urban"
        assert len(URBAN_KNOWLEDGE.injection_text) > 20

    def test_mystery_knowledge_loaded(self):
        from src.genre_knowledge.genres.mystery import MYSTERY_KNOWLEDGE
        assert MYSTERY_KNOWLEDGE.genre == "mystery"
        assert "悬疑" in MYSTERY_KNOWLEDGE.display_name

    def test_fantasy_knowledge_loaded(self):
        from src.genre_knowledge.genres.fantasy import FANTASY_KNOWLEDGE
        assert FANTASY_KNOWLEDGE.genre == "fantasy"
        assert len(FANTASY_KNOWLEDGE.injection_text) > 50

    def test_historical_knowledge_loaded(self):
        from src.genre_knowledge.genres.historical import HISTORICAL_KNOWLEDGE
        assert HISTORICAL_KNOWLEDGE.genre == "historical"
        assert len(HISTORICAL_KNOWLEDGE.injection_text) > 50

    def test_to_prompt_block(self):
        from src.genre_knowledge.genres.wuxia import WUXIA_KNOWLEDGE
        block = WUXIA_KNOWLEDGE.to_prompt_block()
        assert "武侠" in block
        assert "## 类型写作惯例" in block

    def test_to_architect_block(self):
        from src.genre_knowledge.genres.wuxia import WUXIA_KNOWLEDGE
        block = WUXIA_KNOWLEDGE.to_architect_block()
        assert "命名体系" in block or "等级" in block

    def test_to_writer_block(self):
        from src.genre_knowledge.genres.wuxia import WUXIA_KNOWLEDGE
        block = WUXIA_KNOWLEDGE.to_writer_block()
        assert "角色" in block or "叙事" in block

    def test_urban_to_architect_block_fallback(self):
        """没有细粒度字段的类型，architect/writer 回退到 injection_text"""
        from src.genre_knowledge.genres.urban import URBAN_KNOWLEDGE
        arch_block = URBAN_KNOWLEDGE.to_architect_block()
        assert len(arch_block) > 10
        writer_block = URBAN_KNOWLEDGE.to_writer_block()
        assert len(writer_block) > 10


class TestKnowledgeLoader:
    """KnowledgeLoader 测试"""

    def test_loader_created(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        assert len(loader._cache) >= 6

    def test_get_wuxia(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        k = loader.get("wuxia")
        assert k is not None
        assert k.genre == "wuxia"

    def test_get_case_insensitive(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        k = loader.get("WuXia")
        assert k is not None
        assert k.genre == "wuxia"

    def test_get_unknown(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        k = loader.get("nonexistent")
        assert k is None

    def test_get_empty(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        k = loader.get("")
        assert k is None

    def test_inject_to_prompt_match(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        base = "You are a writer."
        result = loader.inject_to_prompt("wuxia", base, role="architect")
        assert len(result) > len(base)
        assert "命名体系" in result

    def test_inject_to_prompt_no_match(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        base = "you are a writer."
        result = loader.inject_to_prompt("unknown_genre", base)
        assert result == base

    def test_inject_architect_vs_writer(self):
        """Architect 和 Writer 接收不同内容"""
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        arch = loader.inject_to_prompt("wuxia", "", role="architect")
        writer = loader.inject_to_prompt("wuxia", "", role="writer")
        assert arch != writer
        # Architect 侧重结构, Writer 侧重创作
        assert len(arch) > 0
        assert len(writer) > 0

    def test_list_all(self):
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        all_genres = loader.list_all()
        assert "wuxia" in all_genres
        assert "scifi" in all_genres
        assert all_genres["wuxia"] == "武侠"


class TestGenreIntegration:
    """集成测试: Architect + ContextBuilder 注入"""

    def test_architect_injection_no_error(self):
        """Architect prompt 中注入不报错"""
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        base = "写一本武侠小说的设定"
        result = loader.inject_to_prompt("wuxia", base, role="architect")
        assert "武侠" in result or "wuxia" in result.lower()
        assert len(result) > len(base)

    def test_context_injection_no_error(self):
        """ContextBuilder 注入不报错"""
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        k = loader.get("wuxia")
        assert k is not None
        block = k.to_writer_block()
        assert len(block) > 10
