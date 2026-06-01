"""
Phase 5 — 后验校验: 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DuplicateHit:
    """一条重复检测命中"""
    new_segment: str
    matched_segment: str
    similarity: float           # 0-1
    source_chapter: int
    severity: str = "medium"    # high / medium / low


@dataclass
class AIStyleIssue:
    """一条 AI 痕迹问题"""
    category: str               # "keyword" / "pattern" / "sentence"
    word: str = ""
    location: str = ""          # 如 "第12段" "第3段"
    suggestion: str = ""


@dataclass
class ConsistencyIssue:
    """一条一致性问题"""
    issue_type: str             # name / state / rule / timeline / hook
    description: str
    source_ref: str = ""        # 如 "roles.md § 沈安"
    chapter_ref: str = ""       # 问题所在的章节段落
    severity: str = "warning"   # error / warning / info


@dataclass
class DuplicationReport:
    """重复检测报告"""
    passed: bool = True
    hits: List[DuplicateHit] = field(default_factory=list)
    total_segments: int = 0
    checked_segments: int = 0
    summary: str = ""


@dataclass
class AIStyleReport:
    """AI 痕迹评估报告"""
    score: int = 0                          # 0-100，越低越好
    level: str = "良好"                      # 良好 / 注意 / 严重
    blacklist_hits: List[AIStyleIssue] = field(default_factory=list)
    sentence_std_ratio: float = 0.0         # 句长标准差/均值
    connector_density: float = 0.0          # 连接词密度
    dialogue_ratio: float = 0.0             # 对白比例
    total_words: int = 0


@dataclass
class ConsistencyReport:
    """一致性校验报告"""
    passed: bool = True
    issues: List[ConsistencyIssue] = field(default_factory=list)
    names_checked: int = 0
    rules_checked: int = 0
    hooks_checked: int = 0


@dataclass
class CheckReport:
    """综合校验报告"""
    project_name: str = ""
    chapter_number: int = 0
    word_count: int = 0

    duplication: Optional[DuplicationReport] = None
    ai_style: Optional[AIStyleReport] = None
    consistency: Optional[ConsistencyReport] = None

    def has_errors(self) -> bool:
        return (
            (self.duplication is not None and not self.duplication.passed) or
            (self.consistency is not None and not self.consistency.passed)
        )

    def has_warnings(self) -> bool:
        return (
            (self.ai_style is not None and self.ai_style.level != "良好") or
            (self.consistency is not None and len(self.consistency.issues) > 0)
        )

    def format_cli(self) -> str:
        """格式化为 CLI 输出"""
        lines = [
            f"🔍 后验校验: {self.project_name} 第{self.chapter_number}章 ({self.word_count}字)",
            "",
        ]

        # 重复检测
        if self.duplication:
            status = "✅ 通过" if self.duplication.passed else "❌ 发现问题"
            lines.append(f"📋 重复检测 — {status}")
            if self.duplication.hits:
                for h in self.duplication.hits:
                    lines.append(f"   ├─ [{h.severity}] 与第{h.source_chapter}章相似 {h.similarity:.0%}")
                    lines.append(f"   │  新: {h.new_segment[:50]}...")
                    lines.append(f"   │  旧: {h.matched_segment[:50]}...")
            elif self.duplication.summary:
                lines.append(f"   {self.duplication.summary}")
            lines.append("")

        # AI 痕迹
        if self.ai_style:
            icon = {"良好": "✅", "注意": "⚠️", "严重": "❌"}.get(self.ai_style.level, "✅")
            lines.append(f"🤖 AI痕迹评估 — {icon} {self.ai_style.level} ({self.ai_style.score}/100)")
            for h in self.ai_style.blacklist_hits[:8]:
                lines.append(f"   ├─ \"{h.word}\" {h.location} {h.suggestion}")
            lines.append(f"   ├─ 句长分布: {self.ai_style.sentence_std_ratio:.2f}")
            lines.append(f"   └─ 对白比例: {self.ai_style.dialogue_ratio:.0%}")
            lines.append("")

        # 一致性
        if self.consistency:
            status = "✅ 通过" if self.consistency.passed else "❌ 发现问题"
            lines.append(f"🔗 一致性校验 — {status}")
            for i in self.consistency.issues:
                sev = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(i.severity, "⚠️")
                lines.append(f"   {sev} {i.description}")
                if i.source_ref:
                    lines.append(f"      来源: {i.source_ref}")
            lines.append("")

        return "\n".join(lines)
