"""武侠/仙侠类型知识 — 开源骨架版"""
from ..base import GenreKnowledge

WUXIA_KNOWLEDGE = GenreKnowledge(
    genre="wuxia",
    display_name="武侠",
    injection_text="""武侠小说设定惯例。注意门派命名、功法体系、江湖规矩。
角色应有表字；正反派均有动机；语言半文半白。
（完整类型知识请使用 InkEdge 完整版）""",

    naming_conventions="""- 角色: 姓名 + 表字 | 功法: [意象] + 诀/术/功/法 | 门派: [特征] + 派/门/教/宗
（完整知识请使用完整版）""",

    hierarchy_systems="""- 功法分阶（如天/地/玄/黄）| 武学境界递进（外功→内功→化境）
（完整知识请使用完整版）""",

    world_rules="""- 功法须有代价 | 正道魔道行为边界 | 江湖规矩
（完整知识请使用完整版）""",

    character_traits="""- 主角应有明确动机+性格缺陷 | 反派有完整背景 | 师徒/同门关系网
（完整知识请使用完整版）""",

    plot_patterns="""- 平静→变故→入门→修炼→初露锋芒→遭遇强敌→获得奇遇→复仇→归隐
（完整知识请使用完整版）""",

    version="1.0",
    description="中国传统武侠、仙侠类型的世界观设定惯例（骨架版，完整版含详细知识）",
)
