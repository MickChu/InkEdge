"""科幻类型知识 — 开源骨架版"""
from ..base import GenreKnowledge

SCIFI_KNOWLEDGE = GenreKnowledge(
    genre="scifi",
    display_name="科幻",
    injection_text="""科幻小说设定惯例。技术需有物理/工程合理性，社会结构与技术水平匹配。
核心技术须有工作原理+能效比+副作用。
（完整类型知识请使用 InkEdge 完整版）""",

    naming_conventions="""- 技术: [功能] + 编号/代号 | 飞船: [名词] + 号/级
（完整知识请使用完整版）""",

    hierarchy_systems="""- 文明: I型行星→II型恒星→III型星系 | 飞船: 护卫→驱逐→巡洋→战列
（完整知识请使用完整版）""",

    world_rules="""- 技术须有代价 | 殖民地文化差异 | 物理漏洞需自圆其说
（完整知识请使用完整版）""",

    character_traits="""- 科学家: 专长+盲区+道德困境 | 工程师: 实用主义 | 领导者: 权衡科技善恶
（完整知识请使用完整版）""",

    plot_patterns="""- 核心: 科技与人性的张力 | 发现异常→调查→揭示真相→技术危机→人性抉择
（完整知识请使用完整版）""",

    version="1.0",
    description="科幻（硬科幻/太空歌剧/赛博朋克）的设定惯例（骨架版）",
)
