# -*- coding: utf-8 -*-
"""
conflict.py — 冲突线追踪

提取每章核心冲突类型和强度, 追踪全书冲突曲线。
分类: 人vs人 / 人vs环境 / 人vs自我
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


# 冲突关键词（按类型分组）
CONFLICT_KEYWORDS = {
    "person_vs_person": {
        # 对抗关系
        "对抗", "对峙", "战斗", "决斗", "争吵", "辩论", "争执",
        "背叛", "欺骗", "威胁", "挑战", "复仇", "暗算", "阴谋",
        "敌人", "对手", "仇人", "劲敌", "宿敌",
        "冷笑", "怒视", "逼问", "质问道", "喝到", "厉声",
    },
    "person_vs_environment": {
        # 环境/命运对抗
        "天灾", "地震", "洪水", "暴风", "大雪", "酷暑", "严寒",
        "绝境", "困境", "险境", "陷阱", "围困", "逃脱",
        "饥饿", "疲惫", "伤痛", "中毒", "疾病",
        "社会", "朝廷", "官府", "门派", "家族",
        "规矩", "法则", "天道", "命运", "宿命",
    },
    "person_vs_self": {
        # 内心冲突
        "犹豫", "挣扎", "纠结", "矛盾", "困惑", "迷茫",
        "愧疚", "悔恨", "自责", "恐惧", "焦虑", "痛苦",
        "选择", "抉择", "取舍", "牺牲",
        "难道", "为何", "为什么", "是否",
        "心魔", "执念", "执拗",
    },
}

# 冲突强度词（权重）
INTENSITY_WEIGHTS = {
    "死": 3, "杀": 3, "血": 3, "战": 3, "毁灭": 3, "崩溃": 3,
    "爆": 2, "裂": 2, "断": 2, "碎": 2, "破": 2,
    "伤": 2, "痛": 2, "怒": 2, "恨": 2, "恐": 2,
    "急": 1, "慌": 1, "躲": 1, "逃": 1, "挡": 1,
}


@dataclass
class ConflictStats:
    """单章冲突统计"""
    chapter: int
    person_vs_person: int = 0
    person_vs_environment: int = 0
    person_vs_self: int = 0
    intensity: float = 0.0  # 0-10 分

    @property
    def dominant(self) -> str:
        types = [
            ("人vs人", self.person_vs_person),
            ("人vs环境", self.person_vs_environment),
            ("人vs自我", self.person_vs_self),
        ]
        return max(types, key=lambda t: t[1])[0]

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "person_vs_person": self.person_vs_person,
            "person_vs_environment": self.person_vs_environment,
            "person_vs_self": self.person_vs_self,
            "dominant": self.dominant,
            "intensity": round(self.intensity, 1),
        }


@dataclass
class ConflictReport:
    """冲突追踪报告"""
    project: str
    stats: List[ConflictStats] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.stats:
            return "无章节数据"

        intensities = [s.intensity for s in self.stats]
        avg = sum(intensities) / len(intensities)
        mins = [s for s in self.stats if s.intensity < 2.0]

        lines = [
            f"冲突追踪: {len(self.stats)} 章",
            f"  平均强度: {avg:.1f}/10",
        ]
        if mins:
            lines.append(f"  低冲突章节 ({len(mins)}):")
            for s in mins[:5]:
                lines.append(f"    第{s.chapter}章 强度 {s.intensity:.1f} ({s.dominant})")

        for w in self.warnings:
            lines.append(w)

        return "\n".join(lines)


class ConflictTracker:
    """冲突线追踪器"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.chapters_dir = self.project_dir / "chapters"

    def analyze(self) -> ConflictReport:
        report = ConflictReport(project=self.project_dir.name)

        if not self.chapters_dir.exists():
            return report

        ch_files = sorted([
            f for f in self.chapters_dir.iterdir()
            if f.suffix in (".md", ".txt")
        ])

        for fpath in ch_files:
            num = self._extract_num(fpath.name)
            text = fpath.read_text(encoding="utf-8")
            stats = self._analyze_chapter(num, text)
            report.stats.append(stats)

        # 检查冲突低谷
        self._check_valleys(report)

        return report

    def _analyze_chapter(self, num: int, text: str) -> ConflictStats:
        stats = ConflictStats(chapter=num)

        # 计数各类冲突关键词
        for ctype, keywords in CONFLICT_KEYWORDS.items():
            count = 0
            for kw in keywords:
                count += text.count(kw)
            setattr(stats, ctype, count)

        # 计算冲突强度 (0-10)
        total_hits = stats.person_vs_person + stats.person_vs_environment + stats.person_vs_self
        if total_hits > 0 and len(text) > 0:
            # 基础分: 冲突密度
            density = total_hits / (len(text) / 1000)  # 每千字冲突词数
            base = min(density * 2, 7)  # 上限7分

            # 强度加权
            intense = 0
            for kw, w in INTENSITY_WEIGHTS.items():
                intense += text.count(kw) * w
            intense_bonus = min(intense / (len(text) / 500), 3)  # 上限3分

            stats.intensity = round(base + intense_bonus, 1)
        else:
            stats.intensity = 0.0

        return stats

    def _check_valleys(self, report: ConflictReport):
        """检测冲突低谷 (连续2章以上强度<2)"""
        if len(report.stats) < 2:
            return

        valley_start = None
        for i, s in enumerate(report.stats):
            if s.intensity < 2.0:
                if valley_start is None:
                    valley_start = i
            else:
                if valley_start is not None and i - valley_start >= 2:
                    chs = [report.stats[j].chapter for j in range(valley_start, i)]
                    report.warnings.append(
                        f"⚠️  冲突低谷: 第{chs[0]}-{chs[-1]}章 持续低强度, "
                        f"建议增加冲突或转折"
                    )
                valley_start = None

        # 结尾也检查
        if valley_start is not None and len(report.stats) - valley_start >= 2:
            chs = [report.stats[j].chapter for j in range(valley_start, len(report.stats))]
            report.warnings.append(
                f"⚠️  冲突低谷 (末尾): 第{chs[0]}-{chs[-1]}章 持续低强度"
            )

    @staticmethod
    def _extract_num(filename: str) -> int:
        match = re.search(r"(\d{4})", filename)
        return int(match.group(1)) if match else 0
