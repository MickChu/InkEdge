"""
Phase 5b — AIStyleScorer（AI 痕迹评分）

规则 + 统计双引擎：
  - 硬规则：关键词黑名单
  - 软统计：句长分布 / 连接词密度 / 对白比例
"""
import re
import logging
from typing import List, Tuple

from .report import AIStyleIssue, AIStyleReport

log = logging.getLogger(__name__)

# ── 黑名单词汇 ──────────────────────────────────────────────────────────────

BLACKLIST = {
    "转折偷懒词": [
        ("突然", "改用动作起句"),
        ("竟然", "展示角色反应而非叙述"),
        ("原来", "通过线索让读者自己发现"),
        ("不料", "用具体事件替代"),
        ("谁知", "删除，让转折自己发生"),
    ],
    "AI套话": [
        ("值得注意的是", "删除或用具体描述替代"),
        ("综上所述", "不适用于小说"),
        ("不仅…更…", "拆为两个独立句"),
        ("在这个…中", "直接描述动作或场景"),
        ("可以看出", "展示而非告知"),
        ("毫无疑问", "让读者自己判断"),
        ("显而易见", "删除"),
    ],
    "表情偷懒": [
        ("微微一笑", "替换为具体的面部动作：嘴角动了一下/眼角皱起"),
        ("嘴角上扬", "替换为更具体的微表情"),
        ("眼中闪过一丝", "太套路，用行为替代"),
        ("深吸一口气", "描写身体感受而非动作标签"),
        ("眼神一凝", "太动漫化，用行为描述"),
    ],
    "过度连接": [
        ("与此同时", "大多数情况可省略"),
        ("另一方面", "暗示切换场景即可"),
        ("紧接着", "直接用动作承接"),
        ("随即", "多数可删"),
    ],
    "空洞强化": [
        ("十分", "删或用具体形容词"),
        ("非常", "删或用具体形容词"),
        ("极其", "删或用具体形容词"),
        ("无比", "删或用具体形容词"),
    ],
}


def _count_blacklist(text: str) -> Tuple[List[AIStyleIssue], int]:
    """统计黑名单词汇命中"""
    issues: List[AIStyleIssue] = []
    total_hits = 0

    for category, words in BLACKLIST.items():
        for word, suggestion in words:
            count = len(re.findall(re.escape(word), text))
            if count > 0:
                total_hits += count
                # 找到每次出现的位置
                for m in re.finditer(re.escape(word), text):
                    pos = m.start()
                    # 估算段落号（每200字1段）
                    para_num = pos // 200 + 1
                    issues.append(AIStyleIssue(
                        category=category,
                        word=word,
                        location=f"第{para_num}段",
                        suggestion=suggestion,
                    ))
                    if len(issues) >= 30:  # 防止爆表
                        break

    return issues, total_hits


def _analyze_sentences(text: str) -> Tuple[float, float, float, int]:
    """分析句式分布"""
    # 分句（按 。！？… 分割）
    sentences = re.split(r'[。！？…\n]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 2]

    if not sentences:
        return 0.0, 0.0, 0.0, 0

    lengths = [len(s) for s in sentences]
    total_words = sum(lengths)

    mean_len = total_words / len(sentences) if sentences else 0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(sentences) if sentences else 0
    std = variance ** 0.5
    std_ratio = std / mean_len if mean_len > 0 else 0

    # 连接词密度
    connectors = r'然而|但是|因为|所以|因此|而且|于是|然后|接着|之后|最终|最后|开始|首先'
    connector_count = len(re.findall(connectors, text))
    connector_density = connector_count / len(sentences) if sentences else 0

    # 对白比例
    dialogue_chars = len(re.findall(r'「[^」]*」|"[^"]*"', text))
    dialogue_ratio = dialogue_chars / total_words if total_words > 0 else 0

    return std_ratio, connector_density, dialogue_ratio, total_words


class AIStyleScorer:
    """AI 痕迹评分器"""

    def __init__(self):
        pass

    def score(self, chapter_text: str) -> AIStyleReport:
        """
        评估章节的 AI 痕迹。

        Returns:
            AIStyleReport (score 0-100, 越低越好)
        """
        # 1. 黑名单统计
        issues, total_blacklist_hits = _count_blacklist(chapter_text)

        # 2. 句式分析
        std_ratio, connector_density, dialogue_ratio, total_words = \
            _analyze_sentences(chapter_text)

        # 3. 综合评分
        # 黑名单密度（每万字命中数）
        blacklist_density = (total_blacklist_hits / total_words * 10000) if total_words > 0 else 0

        # 各维度打分（0-100，越低越好）
        blacklist_score = min(100, blacklist_density * 15)      # ~7次/万字 = 100
        std_score = max(0, (0.5 - std_ratio) * 200) if std_ratio < 0.5 else 0  # <0.5 太均匀
        connector_score = min(100, connector_density * 500)     # 0.2 密度 = 100
        dialogue_score = 0
        if dialogue_ratio < 0.2 or dialogue_ratio > 0.6:       # 理想区间 0.2-0.6
            dialogue_score = min(100, abs(dialogue_ratio - 0.4) * 250)

        # 加权综合
        total_score = (
            blacklist_score * 0.4 +
            std_score * 0.2 +
            connector_score * 0.2 +
            dialogue_score * 0.2
        )
        total_score = round(min(100, total_score))

        # 等级判定
        if total_score <= 25:
            level = "良好"
        elif total_score <= 50:
            level = "注意"
        else:
            level = "严重"

        # 只保留高频/有意义的 issues
        significant_issues = [
            i for i in issues
            if i.category in ("AI套话", "表情偷懒")
            or (i.category == "转折偷懒词" and any(
                w in i.word for w in ("突然", "竟然")
            ))
        ][:8]

        return AIStyleReport(
            score=total_score,
            level=level,
            blacklist_hits=significant_issues,
            sentence_std_ratio=round(std_ratio, 2),
            connector_density=round(connector_density, 2),
            dialogue_ratio=round(dialogue_ratio, 2),
            total_words=total_words,
        )
