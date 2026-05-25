"""历史类型知识 — 开源骨架版"""
from ..base import GenreKnowledge

HISTORICAL_KNOWLEDGE = GenreKnowledge(
    genre="historical",
    display_name="历史",
    injection_text="""历史小说设定惯例。年号/官职/地名/货币/服饰/饮食需与目标朝代一致。
重大历史事件时间线不可篡改。古人思维须符合时代背景。
（完整类型知识请使用 InkEdge 完整版）""",

    version="1.0",
    description="历史/架空历史题材的设定惯例（骨架版）",
)
