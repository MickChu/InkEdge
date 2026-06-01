"""
Phase 6 — 角色状态追踪: 数据模型与持久化

character_state.json 格式:
{
  "project": "书",
  "last_chapter": 10,
  "characters": {
    "沈安": {
      "inventory": [{item, quantity, aquired_chapter, status}],
      "abilities": [{name, level, learned_chapter, mastery}],
      "relationships": {角色名: {status, trust, last_interaction_chapter, last_interaction_summary}},
      "physical_state": "左臂轻伤",
      "location": "天听阁地下废墟出口"
    }
  },
  "snapshots": {"5": "state_snapshot_05.json", "10": "state_snapshot_10.json"}
}
"""
import json
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from copy import deepcopy

log = logging.getLogger(__name__)


@dataclass
class InventoryItem:
    item: str
    quantity: int = 1
    acquired_chapter: int = 0
    last_used_chapter: Optional[int] = None
    status: str = "持有"   # 持有 / 已用 / 丢失
    detail: str = ""


@dataclass
class Ability:
    name: str
    level: str = "入门"
    learned_chapter: int = 0
    last_upgraded_chapter: Optional[int] = None
    mastery: str = "初学"  # 初学 / 熟练 / 精通 / 圆满
    detail: str = ""


@dataclass
class Relationship:
    status: str = "陌生人"  # 同伴 / 盟友 / 陌生人 / 疏远 / 敌对
    trust: int = 0           # -100 ~ 100
    last_interaction_chapter: int = 0
    last_interaction_summary: str = ""


@dataclass
class CharacterState:
    """单个角色的状态"""
    role: str = "unknown"
    inventory: List[InventoryItem] = field(default_factory=list)
    abilities: List[Ability] = field(default_factory=list)
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    physical_state: str = ""
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "inventory": [
                {"item": i.item, "quantity": i.quantity,
                 "acquired_chapter": i.acquired_chapter,
                 "last_used_chapter": i.last_used_chapter,
                 "status": i.status, "detail": i.detail}
                for i in self.inventory
            ],
            "abilities": [
                {"name": a.name, "level": a.level,
                 "learned_chapter": a.learned_chapter,
                 "last_upgraded_chapter": a.last_upgraded_chapter,
                 "mastery": a.mastery, "detail": a.detail}
                for a in self.abilities
            ],
            "relationships": {
                k: {
                    "status": v.status, "trust": v.trust,
                    "last_interaction_chapter": v.last_interaction_chapter,
                    "last_interaction_summary": v.last_interaction_summary,
                }
                for k, v in self.relationships.items()
            },
            "physical_state": self.physical_state,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterState":
        state = cls(
            role=d.get("role", "unknown"),
            physical_state=d.get("physical_state", ""),
            location=d.get("location", ""),
        )
        for item_d in d.get("inventory", []):
            state.inventory.append(InventoryItem(
                item=item_d["item"],
                quantity=item_d.get("quantity", 1),
                acquired_chapter=item_d.get("acquired_chapter", 0),
                last_used_chapter=item_d.get("last_used_chapter"),
                status=item_d.get("status", "持有"),
                detail=item_d.get("detail", ""),
            ))
        for ab_d in d.get("abilities", []):
            state.abilities.append(Ability(
                name=ab_d["name"],
                level=ab_d.get("level", "入门"),
                learned_chapter=ab_d.get("learned_chapter", 0),
                last_upgraded_chapter=ab_d.get("last_upgraded_chapter"),
                mastery=ab_d.get("mastery", "初学"),
                detail=ab_d.get("detail", ""),
            ))
        for name, rel_d in d.get("relationships", {}).items():
            state.relationships[name] = Relationship(
                status=rel_d.get("status", "陌生人"),
                trust=rel_d.get("trust", 0),
                last_interaction_chapter=rel_d.get("last_interaction_chapter", 0),
                last_interaction_summary=rel_d.get("last_interaction_summary", ""),
            )
        return state


class StateStore:
    """角色状态的持久化存储"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.state_dir = os.path.join(project_dir, "state")
        self.state_path = os.path.join(self.state_dir, "character_state.json")
        self.snapshot_dir = os.path.join(self.state_dir, "snapshots")
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def exists(self) -> bool:
        return os.path.exists(self.state_path)

    def load(self) -> Dict[str, CharacterState]:
        """加载角色状态"""
        if not self.exists():
            return {}

        with open(self.state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chars = {}
        for name, char_d in data.get("characters", {}).items():
            chars[name] = CharacterState.from_dict(char_d)

        return chars

    def save(self, characters: Dict[str, CharacterState],
             project_name: str = "", last_chapter: int = 0):
        """保存角色状态"""
        data = {
            "project": project_name,
            "last_chapter": last_chapter,
            "updated_at": "",  # 由调用方设置
            "characters": {
                name: cs.to_dict() for name, cs in characters.items()
            },
            "snapshots": self._list_snapshots(),
        }

        os.makedirs(self.state_dir, exist_ok=True)

        # 人类可读版
        md_path = os.path.join(self.state_dir, "character_state.md")
        self._write_markdown(characters, project_name, last_chapter, md_path)

        # JSON 版
        import datetime
        data["updated_at"] = datetime.datetime.now().isoformat()
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        log.info(f"[StateStore] 保存 {len(characters)} 个角色状态 → {self.state_path}")

    def snapshot(self, characters: Dict[str, CharacterState],
                 chapter_number: int):
        """创建快照"""
        snap_path = os.path.join(
            self.snapshot_dir, f"state_chapter_{chapter_number:04d}.json",
        )
        data = {
            "chapter": chapter_number,
            "characters": {
                name: cs.to_dict() for name, cs in characters.items()
            },
        }
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"[StateStore] 快照已保存: 第{chapter_number}章")

    def rollback(self, chapter_number: int) -> bool:
        """回滚到指定章节的快照"""
        snap_path = os.path.join(
            self.snapshot_dir, f"state_chapter_{chapter_number:04d}.json",
        )
        if not os.path.exists(snap_path):
            return False

        import shutil
        shutil.copy(snap_path, self.state_path)
        log.info(f"[StateStore] 已回滚到第{chapter_number}章快照")
        return True

    def _list_snapshots(self) -> Dict[str, str]:
        snaps = {}
        if os.path.exists(self.snapshot_dir):
            for fname in os.listdir(self.snapshot_dir):
                if fname.startswith("state_chapter_") and fname.endswith(".json"):
                    ch = fname.replace("state_chapter_", "").replace(".json", "")
                    snaps[ch] = fname
        return snaps

    def _write_markdown(self, characters: Dict[str, CharacterState],
                        project_name: str, last_chapter: int, path: str):
        """生成人类可读的 Markdown 版本"""
        lines = [
            f"# {project_name} — 角色状态",
            f"> 更新至第 {last_chapter} 章",
            "",
        ]
        for name, cs in characters.items():
            lines.append(f"## {name} ({cs.role})")
            if cs.location:
                lines.append(f"- 位置: {cs.location}")
            if cs.physical_state:
                lines.append(f"- 身体状态: {cs.physical_state}")
            lines.append("")

            if cs.abilities:
                lines.append("### 能力/功法")
                for a in cs.abilities:
                    lines.append(f"- {a.name}: {a.level} ({a.mastery}) — 习于第{a.learned_chapter}章")
                lines.append("")

            if cs.inventory:
                lines.append("### 物品")
                for i in cs.inventory:
                    status_icon = {"持有": "✅", "已用": "⬜", "丢失": "❌"}.get(i.status, "")
                    lines.append(f"- {status_icon} {i.item} ×{i.quantity} — {i.status}")
                lines.append("")

            if cs.relationships:
                lines.append("### 人际关系")
                for rname, rel in cs.relationships.items():
                    trust_bar = "█" * max(0, rel.trust // 10) + "░" * max(0, 10 - rel.trust // 10)
                    lines.append(f"- {rname}: {rel.status} (信任: {trust_bar} {rel.trust})")
                    if rel.last_interaction_summary:
                        lines.append(f"  最近: Ch{rel.last_interaction_chapter} — {rel.last_interaction_summary}")
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
