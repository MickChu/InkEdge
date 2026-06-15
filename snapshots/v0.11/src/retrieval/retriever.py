"""
SemanticRetriever — 语义检索器

根据当前章节的上下文，从向量存储中检索最相关的历史内容。
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from src.retrieval.vector_store import VectorStore
from src.retrieval.indexer import COL_CHAPTERS, COL_FOUNDATIONS, COL_HOOKS

log = logging.getLogger(__name__)


@dataclass
class RetrievedDocument:
    """检索到的单个文档"""
    text: str
    score: float        # 相似度分数（越高越相关）
    source: str = ""    # 来源文件
    doc_type: str = ""  # 文档类型
    chapter: int = 0    # 所属章节号


@dataclass
class SemanticContext:
    """语义检索结果"""
    chapter_number: int
    hits: List[RetrievedDocument] = field(default_factory=list)
    total_found: int = 0

    def format_for_prompt(self, max_results: int = 5, max_chars: int = 2000) -> str:
        """格式化为 prompt 可用的文本"""
        if not self.hits:
            return "（未找到相关历史内容）"

        lines = ["## 语义相关历史（自动检索）"]

        total = 0
        for hit in self.hits[:max_results]:
            # 精确到字符级别截断
            text = hit.text
            if len(text) > 500:
                text = text[:500].rsplit("。", 1)[0] + "。"

            chapter_str = f"第{hit.chapter}章" if hit.chapter else "设定"
            lines.append(f"\n### {chapter_str} · {hit.doc_type} (相关度: {hit.score:.2f})")
            lines.append(f"> {self._clean_text(text)}")
            total += 1

        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars].rsplit("\n", 1)[0] + "\n…"
        return result

    @staticmethod
    def _clean_text(text: str) -> str:
        """清理文本"""
        text = text.replace("\n\n\n", "\n\n")
        return text.strip()


class SemanticRetriever:
    """语义检索器"""

    def __init__(self, store: VectorStore):
        self.store = store

    def retrieve_for_chapter(
        self,
        chapter_number: int,
        query_text: str,
        n_results: int = 5,
    ) -> SemanticContext:
        """
        为当前章节检索最相关的历史内容。

        Args:
            chapter_number: 当前章节号
            query_text: 查询文本（通常是章节指导 + 角色名）
            n_results: 每个 collection 返回的最大结果数

        Returns:
            SemanticContext with formatted results
        """
        if self.store.count(COL_CHAPTERS) == 0:
            log.warning(f"[Retriever] 向量存储为空，请先运行 index")
            return SemanticContext(chapter_number=chapter_number)

        results = SemanticContext(chapter_number=chapter_number)

        # 1. 搜索章节摘要（最近20章内）
        chapter_results = self.store.query(
            COL_CHAPTERS,
            query_text,
            n_results=n_results,
        )

        if chapter_results and chapter_results["documents"]:
            for i, doc in enumerate(chapter_results["documents"][0]):
                meta = chapter_results["metadatas"][0][i] if chapter_results["metadatas"] else {}
                dist = chapter_results["distances"][0][i] if chapter_results["distances"] else 0.0

                # 排除当前章节自身
                if meta.get("chapter") == chapter_number:
                    continue

                results.hits.append(RetrievedDocument(
                    text=doc,
                    score=1.0 - dist,  # cosine distance → similarity
                    source=meta.get("source", ""),
                    doc_type=meta.get("type", ""),
                    chapter=meta.get("chapter", 0),
                ))

        # 2. 搜索 foundation（世界观/角色设定）
        foundation_results = self.store.query(
            COL_FOUNDATIONS,
            query_text,
            n_results=min(3, n_results),
        )

        if foundation_results and foundation_results["documents"]:
            for i, doc in enumerate(foundation_results["documents"][0]):
                meta = foundation_results["metadatas"][0][i] if foundation_results["metadatas"] else {}
                dist = foundation_results["distances"][0][i] if foundation_results["distances"] else 0.0

                results.hits.append(RetrievedDocument(
                    text=doc,
                    score=1.0 - dist,
                    source=meta.get("source", ""),
                    doc_type=meta.get("type", ""),
                    chapter=0,
                ))

        # 3. 搜索钩子
        hooks_results = self.store.query(
            COL_HOOKS,
            query_text,
            n_results=min(2, n_results),
        )

        if hooks_results and hooks_results["documents"]:
            for i, doc in enumerate(hooks_results["documents"][0]):
                meta = hooks_results["metadatas"][0][i] if hooks_results["metadatas"] else {}
                dist = hooks_results["distances"][0][i] if hooks_results["distances"] else 0.0

                results.hits.append(RetrievedDocument(
                    text=doc,
                    score=1.0 - dist,
                    source=meta.get("source", ""),
                    doc_type="hook",
                    chapter=meta.get("chapter", 0),
                ))

        # 按分数排序，取前 n_results
        results.hits.sort(key=lambda h: h.score, reverse=True)
        results.hits = results.hits[:n_results]
        results.total_found = len(results.hits)

        log.info(f"[Retriever] Ch{chapter_number} 检索到 {results.total_found} 条相关内容")
        return results

    def build_query(self, chapter_number: int, context_dict: Dict[str, str]) -> str:
        """
        为当前章节构建查询文本。
        从上下文包中提取最有信息量的内容作为查询。
        """
        parts = []

        # 优先使用用户指导（如果有的话）
        guidance = context_dict.get("user_guidance", "")
        if guidance:
            parts.append(guidance[:200])

        # 提取当前卷的方向
        volume_map = context_dict.get("volume_map", "")
        if volume_map:
            # 找到当前卷的描述
            current_vol_marker = f"第{chapter_number}章"
            vol_lines = volume_map.split("\n")
            relevant_vol = []
            for line in vol_lines:
                if current_vol_marker in line or "卷" in line:
                    relevant_vol.append(line)
                elif relevant_vol and len("\n".join(relevant_vol)) < 300:
                    relevant_vol.append(line)
            if relevant_vol:
                parts.append(" ".join(relevant_vol[:5]))

        # 提取角色名
        roles = context_dict.get("roles", "")
        if roles:
            # 提取角色名（---ROLE--- name: XXX 模式）
            import re
            role_names = re.findall(r"name:\s*(\S+)", roles)
            if role_names:
                parts.append(f"角色：{', '.join(role_names[:5])}")

        # 提取活跃钩子关键词
        hooks = context_dict.get("pending_hooks", "")
        if hooks:
            # 取前 300 字
            parts.append(hooks[:300])

        query = " ".join(parts)
        # 确保不少于 50 字
        if len(query) < 50:
            query = f"第{chapter_number}章 故事续写"

        return query
