"""
Phase 8 — 类型知识注入系统

定义 GenreKnowledge 数据类和知识加载器。
"""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class GenreKnowledge:
    """一个类型的领域知识"""

    genre: str                          # 唯一标识 (wuxia/scifi/urban/...)
    display_name: str                   # 显示名 (武侠/科幻/都市/...)
    injection_text: str                 # 注入到提示词的完整文本
    naming_conventions: str = ""        # 命名惯例
    hierarchy_systems: str = ""         # 等级/组织体系
    world_rules: str = ""              # 世界观规则模板
    character_traits: str = ""         # 角色特征惯例
    plot_patterns: str = ""            # 叙事模式惯例
    version: str = "1.0"
    description: str = ""

    def to_prompt_block(self) -> str:
        """以 Markdown 格式渲染类型知识块"""
        return f"## 类型写作惯例 ({self.display_name})\n\n{self.injection_text}"

    def to_architect_block(self) -> str:
        """面向 Architect 的知识块（侧重命名和体系）"""
        parts = []
        if self.naming_conventions:
            parts.append(f"### 命名体系\n{self.naming_conventions}")
        if self.hierarchy_systems:
            parts.append(f"### 等级与组织体系\n{self.hierarchy_systems}")
        if self.world_rules:
            parts.append(f"### 世界观规则\n{self.world_rules}")
        if not parts:
            return self.injection_text
        return "\n\n".join(parts)

    def to_writer_block(self) -> str:
        """面向 Writer 的知识块（侧重角色和叙事模式）"""
        parts = []
        if self.character_traits:
            parts.append(f"### 角色塑造惯例\n{self.character_traits}")
        if self.plot_patterns:
            parts.append(f"### 叙事模式惯例\n{self.plot_patterns}")
        if not parts:
            return self.injection_text
        return "\n\n".join(parts)


class KnowledgeLoader:
    """类型知识加载器"""

    def __init__(self):
        self._cache: Dict[str, GenreKnowledge] = {}
        self._load_builtin()

    def get(self, genre: str) -> Optional[GenreKnowledge]:
        """获取指定类型的知识。无匹配返回 None，调用方降级。"""
        if not genre:
            return None
        return self._cache.get(genre.lower())

    def list_all(self) -> Dict[str, str]:
        """列出所有已注册类型"""
        return {k: v.display_name for k, v in self._cache.items()}

    def inject_to_prompt(self, genre: str, base_prompt: str,
                         role: str = "full") -> str:
        """
        向提示词中注入类型知识。

        Args:
            genre: 类型标识 (wuxia/scifi/...)
            base_prompt: 原始提示词
            role: "architect" | "writer" | "full"
        """
        knowledge = self.get(genre)
        if not knowledge:
            return base_prompt

        if role == "architect":
            block = knowledge.to_architect_block()
        elif role == "writer":
            block = knowledge.to_writer_block()
        else:
            block = knowledge.to_prompt_block()

        return f"{base_prompt}\n\n{block}"

    def _load_builtin(self):
        """从 genres/ 目录加载所有内置类型知识"""
        from .genres.wuxia import WUXIA_KNOWLEDGE
        from .genres.scifi import SCIFI_KNOWLEDGE
        from .genres.urban import URBAN_KNOWLEDGE
        from .genres.mystery import MYSTERY_KNOWLEDGE
        from .genres.fantasy import FANTASY_KNOWLEDGE
        from .genres.historical import HISTORICAL_KNOWLEDGE

        for k in [WUXIA_KNOWLEDGE, SCIFI_KNOWLEDGE, URBAN_KNOWLEDGE,
                  MYSTERY_KNOWLEDGE, FANTASY_KNOWLEDGE, HISTORICAL_KNOWLEDGE]:
            self._cache[k.genre.lower()] = k
