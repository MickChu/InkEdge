# -*- coding: utf-8 -*-
"""
density.py — 章节密度分析

统计每章的对话/动作/描写占比, 生成密度曲线。
支持双模式:
  - 查水: 标出"太水"（描写过重）或"太干"（全是对话动作）的章节
  - 灌水: 对密度偏低的章节, 给出可扩展的内容方向和字数建议
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# 网文密度参考基准（百分比）
NORMS_LIGHT = {
    "dialogue": (25, 45),    # 对话
    "action": (30, 50),      # 动作
    "description": (15, 30), # 描写
    "inner": (5, 15),        # 内心
}

# 中文动作动词高频词
ACTION_VERBS = {
    "打", "杀", "冲", "砍", "刺", "劈", "踢", "砸", "推", "拉",
    "跳", "飞", "跑", "奔", "追", "逃", "躲", "闪", "滚", "翻",
    "抓", "握", "捏", "按", "拍", "弹", "击", "射", "炸", "爆",
    "爬", "钻", "闯", "挡", "拦", "劈", "撕", "折", "挥", "扫",
    "转身", "抬手", "踏步", "蹬", "踹", "抡", "甩", "拍",
}

# 描写标记词
DESC_MARKERS = {
    "阳光", "月光", "星光", "灯光", "天空", "云", "风", "雨",
    "山", "水", "湖", "海", "河", "树", "花", "草", "叶",
    "街道", "房屋", "宫殿", "房间", "墙壁", "窗户", "门",
    "空气", "气氛", "温度", "寒冷", "炎热", "寂静", "喧嚣",
    "颜色", "金色", "银色", "红色", "黑色", "白色", "蓝色",
    "声音", "香味", "气味", "光芒", "影子", "轮廓",
    "仿佛", "似乎", "宛若", "如同", "好像",
    "般", "般配", "一般",
}

# 内心独白标记
INNER_MARKERS = {
    "心想", "心道", "暗道", "暗想", "寻思", "忖道",
    "难道", "莫非", "为何", "为什么",
    "感觉", "觉得", "感到", "意识到",
}


@dataclass
class DensityStats:
    """单章密度统计"""
    chapter: int
    total_chars: int
    dialogue_chars: int = 0
    action_chars: int = 0
    description_chars: int = 0
    inner_chars: int = 0

    @property
    def dialogue_pct(self) -> float:
        return self.dialogue_chars / self.total_chars * 100 if self.total_chars else 0

    @property
    def action_pct(self) -> float:
        return self.action_chars / self.total_chars * 100 if self.total_chars else 0

    @property
    def description_pct(self) -> float:
        return self.description_chars / self.total_chars * 100 if self.total_chars else 0

    @property
    def inner_pct(self) -> float:
        return self.inner_chars / self.total_chars * 100 if self.total_chars else 0

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "total_chars": self.total_chars,
            "dialogue_pct": round(self.dialogue_pct, 1),
            "action_pct": round(self.action_pct, 1),
            "description_pct": round(self.description_pct, 1),
            "inner_pct": round(self.inner_pct, 1),
        }


@dataclass
class DensityReport:
    """密度分析报告"""
    project: str
    stats: List[DensityStats] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fill_suggestions: List[str] = field(default_factory=list)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_fill(self, msg: str):
        self.fill_suggestions.append(msg)


class DensityAnalyzer:
    """章节密度分析器"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.chapters_dir = self.project_dir / "chapters"

    def analyze(self) -> DensityReport:
        """分析所有章节"""
        report = DensityReport(project=self.project_dir.name)

        if not self.chapters_dir.exists():
            report.add_warning("无章节目录")
            return report

        # 收集章节文件
        ch_files = sorted([
            f for f in self.chapters_dir.iterdir()
            if f.suffix in (".md", ".txt")
        ])
        if not ch_files:
            report.add_warning("无章节文件")
            return report

        for fpath in ch_files:
            num = self._extract_chapter_num(fpath.name)
            text = fpath.read_text(encoding="utf-8")
            stats = self._analyze_chapter(num, text)
            report.stats.append(stats)

        # 生成警告和建议
        self._check_norms(report)

        return report

    def analyze_fill(self, target_density: str = "description") -> DensityReport:
        """
        灌水模式: 找出密度偏低的章节, 给出可扩展方向

        target_density: 需要提升的密度类型 (dialogue/action/description/inner)
        """
        report = self.analyze()

        for s in report.stats:
            suggestions = []
            current = getattr(s, f"{target_density}_pct", 0)
            needs = 0

            if target_density == "description":
                if current < NORMS_LIGHT["description"][0]:
                    needs = 300 - 500  # 建议加 300-500 字描写
                    suggestions.append(
                        f"第{s.chapter}章 描写密度 {current:.0f}% (偏低), "
                        f"建议增加约{needs}字环境/氛围描写"
                    )
                    suggestions.append("  → 可扩展: 场景氛围渲染、人物外貌细节、环境感官描写")
            elif target_density == "action":
                if current < NORMS_LIGHT["action"][0]:
                    needs = 200 - 400
                    suggestions.append(
                        f"第{s.chapter}章 动作密度 {current:.0f}% (偏低), "
                        f"建议增加约{needs}字动作场面"
                    )
                    suggestions.append("  → 可扩展: 增加小冲突、追逐/打斗细节、紧张对峙")
            elif target_density == "dialogue":
                if current < NORMS_LIGHT["dialogue"][0]:
                    needs = 200 - 400
                    suggestions.append(
                        f"第{s.chapter}章 对话密度 {current:.0f}% (偏低), "
                        f"建议增加约{needs}字对话"
                    )
                    suggestions.append("  → 可扩展: 人物间信息交换、争吵、幽默对话、内心独白转化为对白")
            elif target_density == "inner":
                if current < NORMS_LIGHT["inner"][0]:
                    needs = 100 - 300
                    suggestions.append(
                        f"第{s.chapter}章 内心戏密度 {current:.0f}% (偏低), "
                        f"建议增加约{needs}字内心独白"
                    )
                    suggestions.append("  → 可扩展: 主角对事件的感受、道德困境、情感挣扎")

            for sgg in suggestions:
                report.add_fill(sgg)

        return report

    # ================================================================
    # 内部方法
    # ================================================================

    def _analyze_chapter(self, num: int, text: str) -> DensityStats:
        """分析单章密度"""
        stats = DensityStats(chapter=num, total_chars=len(text))

        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            line_chars = len(stripped)

            # 1. 对话检测: 引导引起或以「开头
            if self._is_dialogue(stripped):
                stats.dialogue_chars += line_chars
                continue

            # 2. 内心独白
            if self._is_inner(stripped):
                stats.inner_chars += line_chars
                continue

            # 3. 动作检测: 高密度动作动词
            action_score = self._action_score(stripped)
            desc_score = self._description_score(stripped)

            if action_score > desc_score:
                stats.action_chars += line_chars
            else:
                stats.description_chars += line_chars

        return stats

    def _is_dialogue(self, line: str) -> bool:
        """检测是否为对话行"""
        # 中文引号
        if line.startswith("「") or line.startswith("『") or line.startswith("“"):
            return True
        # 西文引号
        if line.startswith("\"") and len(line) > 2:
            return True
        # 说/道/问/喊/叫 开头
        if re.match(r"^.{0,4}[说道问喊叫骂吼嚷]", line) and line.endswith("。"):
            # 可能是对话引导句
            return False
        return False

    def _is_inner(self, line: str) -> bool:
        """检测是否为内心独白"""
        for marker in INNER_MARKERS:
            if marker in line:
                return True
        return False

    def _action_score(self, line: str) -> int:
        """计算动作密度分"""
        score = 0
        for verb in ACTION_VERBS:
            score += line.count(verb)
        return score

    def _description_score(self, line: str) -> int:
        """计算描写密度分"""
        score = 0
        for marker in DESC_MARKERS:
            score += line.count(marker) * 2  # 描写词权重更高
        # 长句偏描写
        if len(line) > 50:
            score += 1
        return score

    def _check_norms(self, report: DensityReport):
        """对比基准, 生成警告"""
        for s in report.stats:
            # 描写过高 (>30%)
            if s.description_pct > 35:
                report.add_warning(
                    f"⚠️  第{s.chapter}章 描写占比 {s.description_pct:.0f}% (偏高), "
                    f"可能导致节奏拖沓"
                )
            # 全是对话 (>55%)
            if s.dialogue_pct > 55:
                report.add_warning(
                    f"⚠️  第{s.chapter}章 对话占比 {s.dialogue_pct:.0f}% (偏高), "
                    f"缺少场景支撑"
                )
            # 动作过少 (<20%)
            if s.action_pct < 20 and s.total_chars > 500:
                report.add_warning(
                    f"⚠️  第{s.chapter}章 动作占比 {s.action_pct:.0f}% (偏低), "
                    f"可能缺乏推进感"
                )

    @staticmethod
    def _extract_chapter_num(filename: str) -> int:
        """从文件名提取章节号"""
        # chapter_0001.md → 1
        # 0001_迭代 V2.md → 1
        match = re.search(r"(\d{4})", filename)
        if match:
            return int(match.group(1))
        return 0
