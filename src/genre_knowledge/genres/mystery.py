"""悬疑类型知识 — 开源骨架版"""
from ..base import GenreKnowledge

MYSTERY_KNOWLEDGE = GenreKnowledge(
    genre="mystery",
    display_name="悬疑",
    injection_text="""悬疑小说设定惯例。谜题须先铺设线索再揭示真相，不可凭空出现。
每章保留未解的"为什么"驱动读者。红鲱鱼至少一条。
（完整类型知识请使用 InkEdge 完整版）""",

    version="1.0",
    description="悬疑/推理类型的设定惯例（骨架版）",
)
