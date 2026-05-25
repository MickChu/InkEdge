"""都市类型知识 — 开源版（直接完整开源）"""
from ..base import GenreKnowledge

URBAN_KNOWLEDGE = GenreKnowledge(
    genre="urban",
    display_name="都市",
    injection_text="""都市小说设定惯例。时代背景须明确，社会规则和收入消费要合理。
角色应有现代身份锚点（职业+收入+城市）。对白像真实聊天，不书面。
（本模块内容已包含完整常识级知识，无需完整版）""",

    version="1.0",
    description="都市/现实题材的设定惯例",
)
