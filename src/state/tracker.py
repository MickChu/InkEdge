"""
Phase 6 — StateTracker: LLM 解析章节 → 提取角色状态变化

合并单次 LLM 调用提取三类变化：物品 / 能力 / 关系。
"""
import json
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .character_state import (
    CharacterState, InventoryItem, Ability, Relationship, StateStore,
)

log = logging.getLogger(__name__)


@dataclass
class InventoryChange:
    character: str = ""  # 所属角色
    item: str = ""
    action: str = "acquired"  # "acquired" / "used" / "lost"
    detail: str = ""
    quantity: int = 1


@dataclass
class AbilityChange:
    character: str = ""  # 所属角色
    name: str = ""
    action: str = "learned"  # "learned" / "upgraded" / "used"
    detail: str = ""
    new_level: str = ""


@dataclass
class RelationshipChange:
    character: str = ""  # 角色A
    target: str = ""      # 角色B
    status: str = ""
    trust_delta: int = 0
    summary: str = ""


@dataclass
class ChapterChanges:
    """单章的状态变化汇总"""
    inventory: List[InventoryChange] = field(default_factory=list)
    abilities: List[AbilityChange] = field(default_factory=list)
    relationships: List[RelationshipChange] = field(default_factory=list)
    physical_updates: Dict[str, str] = field(default_factory=dict)
    location_updates: Dict[str, str] = field(default_factory=dict)


CHANGE_EXTRACT_PROMPT = """你是角色状态追踪器。阅读小说章节正文，提取所有角色状态变化。

## 当前状态
{current_state}

## 新章节（第{chapter_number}章）
{chapter_text}

## 任务
提取本章发生的所有变化，以严格 JSON 格式输出：

```json
{{
  "inventory": [
    {{"character": "角色名", "item": "物品名", "action": "acquired|used|lost", "detail": "来源或去向", "quantity": 1}}
  ],
  "abilities": [
    {{"character": "角色名", "name": "能力名", "action": "learned|upgraded|used", "detail": "描述", "new_level": "新等级（仅upgraded时填写）"}}
  ],
  "relationships": [
    {{"character": "角色名A", "target": "角色名B", "status": "同伴|盟友|陌生人|疏远|敌对", "trust_delta": 10, "summary": "本章互动摘要"}}
  ],
  "physical_updates": {{
    "角色名": "身体状态描述（如'左臂受伤'、'中毒未愈'）"
  }},
  "location_updates": {{
    "角色名": "当前所在位置"
  }}
}}
```

规则：
- 只输出本章明确发生的变化，不要猜测
- 如果某个类别没有变化，对应数组/对象为空
- 消耗品（丹药、食物）归为 used
- 信任变化为整数：+10（增进）到 -30（恶化）
- 身体状态只描述本章新发生或变化的情况
"""


class StateTracker:
    """角色状态追踪器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.store = StateStore(project_dir)

    async def extract_changes(self, chapter_text: str, chapter_number: int,
                              current_chars: Dict[str, CharacterState],
                              llm_client) -> ChapterChanges:
        """
        用 LLM 从章节正文中提取状态变化。

        Args:
            chapter_text: 章节全文
            chapter_number: 章号
            current_chars: 当前角色状态
            llm_client: LLM 客户端（需支持 chat 方法）

        Returns:
            ChapterChanges
        """
        # 构建当前状态摘要
        current_summary = self._format_current_state(current_chars)

        prompt = CHANGE_EXTRACT_PROMPT.format(
            current_state=current_summary,
            chapter_number=chapter_number,
            chapter_text=chapter_text[:6000],  # 截断过长的章节
        )

        try:
            response = await llm_client.chat(
                prompt=prompt,
                system_prompt="你是一个精确的数据提取器。只输出 JSON，不要解释。",
                temperature=0.2,
                max_tokens=2000,
            )
            return self._parse_response(response.content)
        except Exception as e:
            log.warning(f"[StateTracker] LLM 提取失败: {e}")
            return ChapterChanges()

    def extract_changes_sync(self, chapter_text: str, chapter_number: int,
                             current_chars: Dict[str, CharacterState]) -> ChapterChanges:
        """同步版本：使用正则回退（无 LLM 可用时）"""
        changes = ChapterChanges()

        # 简单正则提取（精度有限，但无需 LLM）
        # 物品获得
        for m in re.finditer(r'(?:得到|获得|捡起|取出了?|拿出)\s*(?:了\s*)?([\u4e00-\u9fff]{2,10}(?:剑|刀|丹|药|石|令|牌|袋|瓶|匣|卷|书|镜|珠|绳|针|甲|符|印|扇|锤|环|钩|索))',
                              chapter_text):
            changes.inventory.append(InventoryChange(
                item=m.group(1), action="acquired",
                detail=m.group(0), quantity=1,
            ))

        # 能力进步
        for m in re.finditer(r'(?:突破到|达到了|晋入|练成|悟出|学会了?)\s*([\u4e00-\u9fff]{2,8}(?:术|法|功|诀|经|剑|拳|掌|步|劲|气|境|阶|品|重|层))',
                              chapter_text):
            changes.abilities.append(AbilityChange(
                name=m.group(1), action="upgraded",
                detail=m.group(0),
            ))

        return changes

    def apply_changes(self, current_chars: Dict[str, CharacterState],
                      changes: ChapterChanges, chapter_number: int
                      ) -> Dict[str, CharacterState]:
        """将提取的变化应用到当前状态"""
        import copy
        result: Dict[str, CharacterState] = {
            name: copy.deepcopy(cs)
            for name, cs in current_chars.items()
        }

        # 确保所有涉及的角色都存在；未指定角色时默认用第一个已知角色
        known = list(result.keys())
        default_char = known[0] if known else "主角"

        # 给未指定角色的 change 补充默认角色
        for inv in changes.inventory:
            if not inv.character:
                inv.character = default_char
        for ab in changes.abilities:
            if not ab.character:
                ab.character = default_char

        # 物品变化
        for inv in changes.inventory:
            char = result.get(inv.character)
            if not char:
                char = CharacterState()
                result[inv.character] = char

            if inv.action == "acquired":
                # 检查是否已存在
                existing = next((i for i in char.inventory if i.item == inv.item), None)
                if existing:
                    existing.quantity += inv.quantity
                else:
                    char.inventory.append(InventoryItem(
                        item=inv.item, quantity=inv.quantity,
                        acquired_chapter=chapter_number, detail=inv.detail,
                    ))
            elif inv.action == "lost":
                for i in char.inventory:
                    if i.item == inv.item:
                        i.status = "丢失"
                        i.detail = inv.detail
            elif inv.action == "used":
                for i in char.inventory:
                    if i.item == inv.item:
                        i.quantity = max(0, i.quantity - inv.quantity)
                        i.last_used_chapter = chapter_number
                        if i.quantity <= 0:
                            i.status = "已用"

        # 能力变化
        for ab in changes.abilities:
            char = result.get(ab.character)
            if not char:
                char = CharacterState()
                result[ab.character] = char

            if ab.action == "learned":
                char.abilities.append(Ability(
                    name=ab.name, level=ab.new_level or "入门",
                    learned_chapter=chapter_number, detail=ab.detail,
                ))
            elif ab.action == "upgraded":
                existing = next((a for a in char.abilities if a.name == ab.name), None)
                if existing:
                    existing.last_upgraded_chapter = chapter_number
                    if ab.new_level:
                        existing.level = ab.new_level
                    existing.mastery = "熟练"
                else:
                    char.abilities.append(Ability(
                        name=ab.name, level=ab.new_level or "未知",
                        learned_chapter=chapter_number, mastery="初学",
                    ))

        # 关系变化
        for rel in changes.relationships:
            char = result.get(rel.character)
            if not char:
                char = CharacterState()
                result[rel.character] = char

            if rel.target not in char.relationships:
                char.relationships[rel.target] = Relationship()

            existing = char.relationships[rel.target]
            existing.last_interaction_chapter = chapter_number
            existing.last_interaction_summary = rel.summary
            existing.trust = max(-100, min(100, existing.trust + rel.trust_delta))
            if rel.status:
                existing.status = rel.status

            # 双向关系
            target_char = result.get(rel.target)
            if target_char:
                if rel.character not in target_char.relationships:
                    target_char.relationships[rel.character] = Relationship()
                target_rel = target_char.relationships[rel.character]
                target_rel.last_interaction_chapter = chapter_number
                if rel.status:
                    target_rel.status = rel.status

        # 身体状态更新
        for name, state in changes.physical_updates.items():
            if name in result:
                result[name].physical_state = state
            else:
                cs = CharacterState(physical_state=state)
                result[name] = cs

        # 位置更新
        for name, loc in changes.location_updates.items():
            if name in result:
                result[name].location = loc
            else:
                cs = CharacterState(location=loc)
                result[name] = cs

        return result

    def format_for_context(self, characters: Dict[str, CharacterState],
                           max_chars: int = 1500) -> str:
        """将角色状态格式化为 Writer 上下文"""
        if not characters:
            return ""

        lines = ["## 当前角色状态", ""]
        for name, cs in characters.items():
            parts = []

            if cs.location:
                parts.append(f"位于{cs.location}")
            if cs.physical_state:
                parts.append(cs.physical_state)

            item_str = ""
            active_items = [i for i in cs.inventory if i.status == "持有"]
            if active_items:
                items = [f"{i.item}×{i.quantity}" for i in active_items[:5]]
                item_str = f"持有: {', '.join(items)}"
                if len(active_items) > 5:
                    item_str += f" 等{len(active_items)}件"

            ab_str = ""
            if cs.abilities:
                abs_list = [f"{a.name}({a.level}, {a.mastery})" for a in cs.abilities[:5]]
                ab_str = f"能力: {', '.join(abs_list)}"

            rel_strs = []
            for rname, rel in cs.relationships.items():
                if rel.last_interaction_chapter > 0:
                    rel_strs.append(f"对{rname}: {rel.status}(信任{rel.trust})")

            line = f"- **{name}**({cs.role}): "
            # parts 是 list，先展平
            flat_parts = [item_str, ab_str] if item_str or ab_str else []
            flat_parts = parts + flat_parts + rel_strs
            line += " · ".join(p for p in flat_parts if p)
            lines.append(line)

        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n(状态过长，已截断)"
        return result

    # ── 内部辅助 ─────────────────────────────────────────────────

    def _format_current_state(self, characters: Dict[str, CharacterState]) -> str:
        if not characters:
            return "（尚无角色状态记录）"

        lines = []
        for name, cs in characters.items():
            lines.append(f"\n### {name} ({cs.role})")
            if cs.location:
                lines.append(f"位置: {cs.location}")
            if cs.inventory:
                items = [f"{i.item}×{i.quantity}({i.status})" for i in cs.inventory]
                lines.append(f"物品: {', '.join(items)}")
            if cs.abilities:
                abs_list = [f"{a.name}({a.level})" for a in cs.abilities]
                lines.append(f"能力: {', '.join(abs_list)}")
            if cs.relationships:
                for rname, rel in cs.relationships.items():
                    lines.append(f"关系-{rname}: {rel.status} (信任{rel.trust})")
        return "\n".join(lines)

    def _parse_response(self, content: str) -> ChapterChanges:
        """从 LLM 响应中解析 JSON"""
        # 尝试提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            log.warning("[StateTracker] 未在响应中找到 JSON")
            return ChapterChanges()

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            log.warning(f"[StateTracker] JSON 解析失败: {e}")
            return ChapterChanges()

        changes = ChapterChanges()

        for inv_d in data.get("inventory", []):
            changes.inventory.append(InventoryChange(
                item=inv_d.get("item", ""),
                action=inv_d.get("action", "acquired"),
                detail=inv_d.get("detail", ""),
                quantity=int(inv_d.get("quantity", 1)),
            ))

        for ab_d in data.get("abilities", []):
            changes.abilities.append(AbilityChange(
                name=ab_d.get("name", ""),
                action=ab_d.get("action", "learned"),
                detail=ab_d.get("detail", ""),
                new_level=ab_d.get("new_level", ""),
            ))

        for rel_d in data.get("relationships", []):
            changes.relationships.append(RelationshipChange(
                character=rel_d.get("character", ""),
                status=rel_d.get("status", ""),
                trust_delta=int(rel_d.get("trust_delta", 0)),
                summary=rel_d.get("summary", ""),
            ))

        changes.physical_updates = data.get("physical_updates", {})
        changes.location_updates = data.get("location_updates", {})

        return changes

    def _ensure_char_exists(self, result: Dict, name: str):
        if name and name not in result:
            result[name] = CharacterState(role="配角")
        return name in result
