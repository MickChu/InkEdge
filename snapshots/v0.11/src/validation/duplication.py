"""
Phase 5a — DuplicationChecker（重复检测）

利用现有 VectorStore 做语义相似度比较。
对章节分段后，每段在已有索引中搜索最相似段落。
"""
import logging
from typing import List, Optional, Dict, Any

from .report import DuplicateHit, DuplicationReport

log = logging.getLogger(__name__)

# 默认阈值
DEFAULT_SIMILARITY_THRESHOLD = 0.15   # ChromaDB cosine distance → 越低越相似
# 分段大小
CHUNK_MIN_CHARS = 80
CHUNK_MAX_CHARS = 600


def _segment_text(text: str, min_chars: int = CHUNK_MIN_CHARS,
                  max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
    """将文本按自然段落边界分段"""
    # 先按空行分割
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    segments = []

    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            if len(current) >= min_chars:
                segments.append(current)
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if len(current) >= min_chars:
        segments.append(current)
    elif current and segments:
        segments[-1] += "\n\n" + current

    return segments


class DuplicationChecker:
    """重复检测器"""

    def __init__(self, threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self.threshold = threshold

    def check(self, chapter_text: str, store, skip_chapter: int = 0) -> DuplicationReport:
        """
        检查章节是否有与历史内容的重复。

        Args:
            chapter_text: 新章节全文
            store: VectorStore 实例（已构建索引）
            skip_chapter: 跳过此章节号的匹配（排除自匹配）

        Returns:
            DuplicationReport
        """
        segments = _segment_text(chapter_text)

        if len(segments) < 2:
            return DuplicationReport(
                passed=True,
                total_segments=len(segments),
                checked_segments=0,
                summary="章节过短，跳过重复检测",
            )

        hits: List[DuplicateHit] = []

        for i, seg in enumerate(segments):
            if len(seg) < CHUNK_MIN_CHARS:
                continue

            # 在 chapters 和 foundations 两个 collection 中搜索
            for col_name in ("chapters", "foundations"):
                try:
                    result = store.query(col_name, seg, n_results=2)
                except Exception:
                    continue

                if not result["documents"] or not result["documents"][0]:
                    continue

                for j, doc in enumerate(result["documents"][0]):
                    distance = result["distances"][0][j]
                    # ChromaDB 返回 cosine distance: 0=完全一样, 2=完全相反
                    similarity = 1 - (distance / 2)  # 转到 0-1 范围

                    if distance <= self.threshold:
                        meta = result["metadatas"][0][j] if result["metadatas"] else {}
                        source_ch = meta.get("chapter", 0) if isinstance(meta, dict) else 1

                        # 排除自匹配
                        if skip_chapter and int(source_ch) == skip_chapter:
                            continue

                        severity = "low"
                        if distance <= self.threshold * 0.5:
                            severity = "high"
                        elif distance <= self.threshold * 0.75:
                            severity = "medium"

                        hits.append(DuplicateHit(
                            new_segment=seg[:120],
                            matched_segment=doc[:120],
                            similarity=round(similarity, 3),
                            source_chapter=int(source_ch) if source_ch else 1,
                            severity=severity,
                        ))
                        break  # 每段在每个 collection 中只取最近的一条

        # 去重：连续多段命中同一源章节 → 合并
        hits = _deduplicate_hits(hits)

        # 只保留 medium 和 high
        significant = [h for h in hits if h.severity in ("medium", "high")]

        passed = len(significant) == 0
        summary = ""
        if passed:
            summary = "未发现显著重复"
        else:
            high_count = sum(1 for h in significant if h.severity == "high")
            med_count = sum(1 for h in significant if h.severity == "medium")
            parts = []
            if high_count:
                parts.append(f"{high_count}处高度疑似")
            if med_count:
                parts.append(f"{med_count}处中度疑似")
            summary = "，".join(parts)

        return DuplicationReport(
            passed=passed,
            hits=significant,
            total_segments=len(segments),
            checked_segments=sum(1 for s in segments if len(s) >= CHUNK_MIN_CHARS),
            summary=summary,
        )


def _deduplicate_hits(hits: List[DuplicateHit]) -> List[DuplicateHit]:
    """合并连续命中同一源章节的 hit"""
    if len(hits) <= 1:
        return hits

    merged = [hits[0]]
    for h in hits[1:]:
        prev = merged[-1]
        if h.source_chapter == prev.source_chapter and h.similarity > prev.similarity * 0.85:
            # 同源章节、相似度接近 → 只保留更相似的那个
            if h.similarity > prev.similarity:
                merged[-1] = h
        else:
            merged.append(h)

    return merged
