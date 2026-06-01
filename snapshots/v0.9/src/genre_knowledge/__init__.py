"""
Phase 8 — 类型知识注入系统 (Genre Knowledge Injection)

可插拔的类型知识模块。每个类型提供：
- 命名惯例
- 等级/组织体系
- 世界观规则
- 角色特征惯例
- 叙事模式惯例

使用方式:
    from src.genre_knowledge import KnowledgeLoader
    loader = KnowledgeLoader()
    prompt = loader.inject_to_prompt("wuxia", base_prompt, role="architect")
"""
from .base import GenreKnowledge, KnowledgeLoader

__all__ = ["GenreKnowledge", "KnowledgeLoader"]
