"""
Context Builder — 为章节写作组装上下文包

职责：
1. 读取 foundation 文件（story_frame, roles, book_rules, pending_hooks, volume_map）
2. 读取已写章节摘要和当前状态
3. 按优先级裁剪，组装成 ChapterContext
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.utils.file_io import read_file

log = logging.getLogger(__name__)

# 单节上下文字符预算
CONTEXT_BUDGETS = {
    "story_frame": 2000,          # 世界观 + 核心冲突
    "volume_map": 1500,           # 当前卷的方向
    "roles": 3000,                # 角色卡（截取相关角色）
    "book_rules": 500,            # YAML 硬限制
    "pending_hooks": 1000,        # 活跃伏笔
    "chapter_summaries": 2000,    # 最近5章摘要
    "current_state": 500,         # 当前状态
    "style_guide": 2000,          # 风格指南
    "semantic_hits": 1500,        # 语义检索结果
    "genre_knowledge": 800,       # 类型知识
    "total": 8000,                # 总预算
}


@dataclass
class ChapterContext:
    """章节写作上下文"""
    chapter_number: int
    story_frame: str = ""
    volume_map: str = ""
    roles: str = ""
    book_rules: str = ""
    pending_hooks: str = ""
    chapter_summaries: str = ""
    current_state: str = ""
    style_guide: str = ""
    genre_knowledge: str = ""
    semantic_hits: str = ""
    user_guidance: str = ""

    def build_prompt_context(self) -> str:
        """组装为写入器 prompt 的上下文段落"""
        parts = []

        if self.story_frame:
            parts.append(f"## 故事设定\n{self._truncate(self.story_frame, CONTEXT_BUDGETS['story_frame'])}")
        if self.volume_map:
            parts.append(f"## 卷大纲\n{self._truncate(self.volume_map, CONTEXT_BUDGETS['volume_map'])}")
        if self.roles:
            parts.append(f"## 角色设定\n{self._truncate(self.roles, CONTEXT_BUDGETS['roles'])}")
        if self.pending_hooks:
            parts.append(f"## 活跃伏笔\n{self._truncate(self.pending_hooks, CONTEXT_BUDGETS['pending_hooks'])}")
        if self.chapter_summaries:
            parts.append(f"## 前情摘要\n{self._truncate(self.chapter_summaries, CONTEXT_BUDGETS['chapter_summaries'])}")
        if self.book_rules:
            parts.append(f"## 创作规则\n{self._truncate(self.book_rules, CONTEXT_BUDGETS['book_rules'])}")
        if self.current_state:
            parts.append(f"## 当前状态\n{self._truncate(self.current_state, CONTEXT_BUDGETS['current_state'])}")
        if self.style_guide:
            parts.append(f"## 风格指南\n{self._truncate(self.style_guide, CONTEXT_BUDGETS['style_guide'])}")
        if self.semantic_hits:
            parts.append(f"## 语义相关\n{self._truncate(self.semantic_hits, CONTEXT_BUDGETS['semantic_hits'])}")
        if self.genre_knowledge:
            parts.append(f"## 类型惯例\n{self._truncate(self.genre_knowledge, CONTEXT_BUDGETS['genre_knowledge'])}")

        context_text = "\n\n---\n\n".join(parts)
        return self._truncate(context_text, CONTEXT_BUDGETS["total"])

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        # 尽量在段落边界截断
        truncated = text[:max_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.7:
            return truncated[:last_newline] + "\n…"
        return truncated + "…"


class ContextBuilder:
    """上下文组装器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self._cache = {}

    def build(self, chapter_number: int, user_guidance: str = "",
             genre: str = "") -> ChapterContext:
        """组装指定章节的上下文"""
        ctx = ChapterContext(
            chapter_number=chapter_number,
            user_guidance=user_guidance,
        )

        # 读取 foundation 文件
        story_dir = self.project_dir
        ctx.story_frame = self._read(story_dir, "story_frame.md")
        ctx.volume_map = self._read(story_dir, "volume_map.md")
        ctx.roles = self._read(story_dir, "roles.md")
        ctx.book_rules = self._read(story_dir, "book_rules.md")

        # 风格指南（如果存在）
        ctx.style_guide = self._read(story_dir, "style_guide.md")

        # 类型知识注入
        if genre:
            from src.genre_knowledge import KnowledgeLoader
            loader = KnowledgeLoader()
            knowledge = loader.get(genre)
            if knowledge:
                ctx.genre_knowledge = knowledge.to_writer_block()

        # 语义检索（如果向量存储已初始化）
        ctx.semantic_hits = self._semantic_search(story_dir, chapter_number, ctx)

        # 状态文件
        ctx.pending_hooks = self._read(story_dir, "pending_hooks.md")
        ctx.current_state = self._read(story_dir, "current_state.md")

        # 章节摘要（最近5章）
        ctx.chapter_summaries = self._build_summaries(chapter_number)

        # 精简：如果是第1章，裁剪不需要的内容
        if chapter_number == 1:
            ctx.chapter_summaries = "（这是第1章，没有前情摘要）"
            ctx.current_state = "（这是第1章，世界处于初始状态）"

        log.info(f"[ContextBuilder] 上下文组装完成 (ch{chapter_number}, {len(ctx.build_prompt_context())} 字)")
        return ctx

    def _read(self, directory: str, filename: str) -> str:
        """读取文件，失败返回空"""
        path = os.path.join(directory, filename)
        if path in self._cache:
            return self._cache[path]
        content = read_file(path, default="")
        self._cache[path] = content
        return content

    def _build_summaries(self, current_chapter: int) -> str:
        """构建前5章摘要"""
        summary_path = os.path.join(self.project_dir, "chapter_summaries.md")
        content = self._read(self.project_dir, "chapter_summaries.md")
        if not content:
            return "（暂无前情摘要）"

        # 解析摘要文件：每行格式 "N. 摘要"
        lines = content.strip().split("\n")
        recent = []
        start = max(0, current_chapter - 6)

        for line in lines:
            # 匹配 "N. 内容" 或 "第N章 内容"
            stripped = line.strip()
            if not stripped:
                continue
            # 尝试提取章号
            try:
                parts = stripped.split(".", 1)
                if len(parts) == 2:
                    ch_num = int(parts[0].strip())
                    if start <= ch_num < current_chapter:
                        recent.append(stripped)
            except ValueError:
                pass

        if not recent:
            return "（暂无前情摘要）"

        return "\n".join(recent[-5:])  # 最近5章

    def _semantic_search(self, project_dir: str, chapter_number: int,
                        ctx: 'ChapterContext') -> str:
        """执行语义检索，返回格式化的相关历史内容"""
        # 检查 ChromaDB 是否已初始化
        chromadir = os.path.join(project_dir, ".chroma")
        if not os.path.exists(chromadir):
            return ""

        try:
            from src.retrieval import VectorStore, SemanticRetriever
            store = VectorStore(project_dir)

            # 检查是否有索引内容
            if store.count("chapters") == 0:
                return ""

            retriever = SemanticRetriever(store)

            # 构建查询
            context_dict = {
                "user_guidance": ctx.user_guidance,
                "volume_map": ctx.volume_map,
                "roles": ctx.roles,
                "pending_hooks": ctx.pending_hooks,
            }
            query = retriever.build_query(chapter_number, context_dict)

            # 执行检索
            results = retriever.retrieve_for_chapter(
                chapter_number,
                query,
                n_results=5,
            )

            formatted = results.format_for_prompt(max_results=5, max_chars=1500)
            if formatted:
                log.info(f"[ContextBuilder] 语义检索: {results.total_found} 条结果")
            return formatted

        except Exception as e:
            log.debug(f"[ContextBuilder] 语义检索跳过: {e}")
            return ""


def load_chapter_context(project_dir: str, chapter_number: int,
                         user_guidance: str = "") -> ChapterContext:
    """便捷函数"""
    builder = ContextBuilder(project_dir)
    return builder.build(chapter_number, user_guidance)
