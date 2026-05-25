"""奇幻类型知识 — 开源骨架版"""
from ..base import GenreKnowledge

FANTASY_KNOWLEDGE = GenreKnowledge(
    genre="fantasy",
    display_name="奇幻",
    injection_text="""西方奇幻设定惯例。注意魔法体系、种族设计、英雄之旅结构。
每个种族的生理特征+文化传统需有区分度。
（完整类型知识请使用 InkEdge 完整版）""",

    version="1.0",
    description="西方奇幻（中土世界/龙与地下城风格）的设定惯例（骨架版）",
)
