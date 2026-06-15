# -*- coding: utf-8 -*-
"""
foreshadow.py — 结构化伏笔追踪

升级 pending_hooks.md 从静态文本 → JSON 结构
支持: 埋设 → 提醒 → 回收, 跨章追踪
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ForeshadowEntry:
    """单条伏笔"""
    id: str                          # 唯一 id, 如 hook_001
    description: str                 # 伏笔内容
    planted_chapter: int             # 埋设章号
    status: str = "pending"          # pending / reminded / resolved
    reminded_chapter: int = 0        # 最后提醒章号
    resolved_chapter: int = 0        # 回收章号
    resolution: str = ""             # 回收说明
    category: str = "plot"           # plot / character / world / item
    priority: str = "normal"         # normal / major (会影响主线)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "planted_chapter": self.planted_chapter,
            "status": self.status,
            "reminded_chapter": self.reminded_chapter,
            "resolved_chapter": self.resolved_chapter,
            "resolution": self.resolution,
            "category": self.category,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ForeshadowEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ForeshadowReport:
    """伏笔追踪报告"""
    total: int = 0
    pending: List[ForeshadowEntry] = field(default_factory=list)
    reminded: List[ForeshadowEntry] = field(default_factory=list)
    resolved: List[ForeshadowEntry] = field(default_factory=list)
    overdue: List[ForeshadowEntry] = field(default_factory=list)  # 超过20章未提醒

    def summary(self) -> str:
        lines = [
            f"伏笔追踪: 总计 {self.total} 条",
            f"  待回收: {len(self.pending)}",
            f"  已提醒: {len(self.reminded)}",
            f"  已回收: {len(self.resolved)}",
        ]
        if self.overdue:
            lines.append(f"  ⚠️ 逾期未提醒: {len(self.overdue)} 条")
            for h in self.overdue:
                lines.append(f"    {h.id}: {h.description[:50]} (第{h.planted_chapter}章埋设)")
        return "\n".join(lines)


class ForeshadowTracker:
    """伏笔追踪器"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.db_path = self.project_dir / "foreshadow.json"
        self.entries: List[ForeshadowEntry] = []
        self._load()

    # ============================================================
    # CRUD
    # ============================================================

    def add(self, description: str, planted_chapter: int,
            category: str = "plot", priority: str = "normal") -> ForeshadowEntry:
        """添加新伏笔"""
        next_id = f"hook_{len(self.entries) + 1:03d}"
        entry = ForeshadowEntry(
            id=next_id,
            description=description,
            planted_chapter=planted_chapter,
            category=category,
            priority=priority,
        )
        self.entries.append(entry)
        self._save()
        return entry

    def remind(self, hook_id: str, chapter: int):
        """标记为已提醒"""
        for e in self.entries:
            if e.id == hook_id:
                e.status = "reminded"
                e.reminded_chapter = chapter
                break
        self._save()

    def resolve(self, hook_id: str, chapter: int, resolution: str = ""):
        """标记为已回收"""
        for e in self.entries:
            if e.id == hook_id:
                e.status = "resolved"
                e.resolved_chapter = chapter
                e.resolution = resolution
                break
        self._save()

    def report(self, current_chapter: int = 0) -> ForeshadowReport:
        """生成追踪报告"""
        rpt = ForeshadowReport(total=len(self.entries))
        for e in self.entries:
            if e.status == "pending":
                rpt.pending.append(e)
                # 超过20章未提醒 → 逾期
                if current_chapter > 0 and current_chapter - e.planted_chapter > 20:
                    rpt.overdue.append(e)
            elif e.status == "reminded":
                rpt.reminded.append(e)
            elif e.status == "resolved":
                rpt.resolved.append(e)
        return rpt

    # ============================================================
    # 迁移: 从 pending_hooks.md → foreshadow.json
    # ============================================================

    def migrate_from_md(self) -> int:
        """从旧的 pending_hooks.md 迁移数据"""
        md_path = self.project_dir / "pending_hooks.md"
        if not md_path.exists():
            return 0

        text = md_path.read_text(encoding="utf-8").strip()
        if not text:
            return 0

        # 简单解析: 每行一条伏笔
        count = 0
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 去掉序号前缀: "1. " / "- " / "* "
            desc = line.lstrip("0123456789. - * \t")
            if len(desc) > 5:
                self.add(description=desc, planted_chapter=1)
                count += 1

        return count

    # ============================================================
    # 内部
    # ============================================================

    def _save(self):
        data = [e.to_dict() for e in self.entries]
        self.db_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self):
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding="utf-8"))
                self.entries = [ForeshadowEntry.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self.entries = []
