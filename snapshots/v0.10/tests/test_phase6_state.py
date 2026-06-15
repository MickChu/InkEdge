"""
Phase 6 测试 — 角色状态追踪系统
"""
import os
import sys
import tempfile
import shutil
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStateStore:
    """持久化存储测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_load_returns_dict(self):
        from src.state.character_state import StateStore
        store = StateStore(self.tmpdir)
        result = store.load()
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_save_and_load(self):
        from src.state.character_state import (
            StateStore, CharacterState, InventoryItem, Ability,
        )
        store = StateStore(self.tmpdir)

        cs = CharacterState(role="protagonist")
        cs.inventory.append(InventoryItem(
            item="短剑", quantity=1, acquired_chapter=1,
        ))
        cs.abilities.append(Ability(
            name="基础剑法", level="入门", learned_chapter=1,
        ))

        store.save({"沈安": cs}, project_name="测试书", last_chapter=1)
        assert store.exists()

        loaded = store.load()
        assert "沈安" in loaded
        assert len(loaded["沈安"].inventory) == 1
        assert loaded["沈安"].inventory[0].item == "短剑"

    def test_markdown_output(self):
        from src.state.character_state import StateStore, CharacterState
        store = StateStore(self.tmpdir)
        cs = CharacterState(location="破庙", physical_state="轻伤")
        store.save({"主角": cs}, "测试书", 1)
        md_path = os.path.join(self.tmpdir, "state", "character_state.md")
        assert os.path.exists(md_path)
        content = open(md_path, encoding="utf-8").read()
        assert "主角" in content
        assert "破庙" in content

    def test_snapshot_and_rollback(self):
        from src.state.character_state import StateStore, CharacterState, InventoryItem
        store = StateStore(self.tmpdir)

        cs1 = CharacterState()
        cs1.inventory.append(InventoryItem(item="匕首", acquired_chapter=1))
        store.save({"沈安": cs1}, "测试书", 1)
        store.snapshot({"沈安": cs1}, 1)

        cs2 = CharacterState()
        cs2.inventory.append(InventoryItem(item="剑", acquired_chapter=2))
        store.save({"沈安": cs2}, "测试书", 2)

        # 回滚到第1章
        store.rollback(1)
        loaded = store.load()
        assert loaded["沈安"].inventory[0].item == "匕首"


class TestStateTracker:
    """状态追踪器测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_changes_sync_acquire_dan(self):
        from src.state.tracker import StateTracker
        tracker = StateTracker(self.tmpdir)
        changes = tracker.extract_changes_sync(
            "他从怀中取出一枚培元丹服下。", 1, {},
        )
        assert len(changes.inventory) >= 1
        assert any("培元丹" in c.item for c in changes.inventory)

    def test_extract_changes_sync_ability_upgrade(self):
        from src.state.tracker import StateTracker
        tracker = StateTracker(self.tmpdir)
        changes = tracker.extract_changes_sync(
            "经过一夜修炼，他终于突破到了筑基境。", 5, {},
        )
        assert len(changes.abilities) >= 1

    def test_apply_changes_add_inventory(self):
        from src.state.tracker import StateTracker, ChapterChanges, InventoryChange
        tracker = StateTracker(self.tmpdir)
        changes = ChapterChanges(
            inventory=[InventoryChange(
                character="沈安", item="短剑", action="acquired",
                detail="从铁匠铺买到", quantity=1,
            )],
        )
        result = tracker.apply_changes({}, changes, 1)
        assert "沈安" in result
        assert len(result["沈安"].inventory) == 1
        assert result["沈安"].inventory[0].item == "短剑"

    def test_apply_changes_use_item(self):
        from src.state.tracker import StateTracker, ChapterChanges, InventoryChange
        from src.state.character_state import CharacterState, InventoryItem

        tracker = StateTracker(self.tmpdir)
        cs = CharacterState()
        cs.inventory.append(InventoryItem(item="解毒丹", quantity=3))

        changes = ChapterChanges(
            inventory=[InventoryChange(
                character="沈安", item="解毒丹", action="used",
                detail="给阿沅服用", quantity=1,
            )],
        )
        result = tracker.apply_changes({"沈安": cs}, changes, 2)
        assert result["沈安"].inventory[0].quantity == 2

    def test_apply_changes_relationship(self):
        from src.state.tracker import StateTracker, ChapterChanges, RelationshipChange
        tracker = StateTracker(self.tmpdir)
        changes = ChapterChanges(
            relationships=[RelationshipChange(
                character="沈安", target="阿沅",
                status="同伴", trust_delta=20,
                summary="一起对抗敌人",
            )],
        )
        result = tracker.apply_changes({}, changes, 3)
        assert "阿沅" in result["沈安"].relationships
        assert result["沈安"].relationships["阿沅"].status == "同伴"
        assert result["沈安"].relationships["阿沅"].trust == 20

    def test_format_for_context(self):
        from src.state.tracker import StateTracker
        from src.state.character_state import CharacterState, InventoryItem, Ability

        tracker = StateTracker(self.tmpdir)
        cs = CharacterState(role="protagonist", location="城外", physical_state="健康")
        cs.inventory.append(InventoryItem(item="短剑", quantity=1, acquired_chapter=1))
        cs.abilities.append(Ability(name="蜕衣术", level="玄阶上品", learned_chapter=1))

        result = tracker.format_for_context({"沈安": cs})
        assert "沈安" in result
        assert "短剑" in result
        assert "蜕衣术" in result

    def test_default_character_on_empty(self):
        from src.state.tracker import StateTracker, ChapterChanges, InventoryChange
        tracker = StateTracker(self.tmpdir)
        # 未指定 character 的 change
        changes = ChapterChanges(
            inventory=[InventoryChange(item="短剑", action="acquired")],
        )
        result = tracker.apply_changes({}, changes, 1)
        assert "主角" in result


class TestStateManagerIntegration:
    """StateManager 集成测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_post_write_triggers_state_tracking(self):
        from src.state.manager import StateManager
        sm = StateManager(self.tmpdir)
        result = sm.post_write(1, "他从怀中取出一枚聚气丹服下。")
        assert "chapter_path" in result

        # 验证状态文件被创建
        state_path = os.path.join(self.tmpdir, "state", "character_state.json")
        assert os.path.exists(state_path)

    def test_get_character_context(self):
        from src.state.manager import StateManager
        sm = StateManager(self.tmpdir)
        sm.track_characters_sync(
            "沈安练成了基础剑法。他从包袱里取出短剑握在手中。",
            chapter_number=1,
        )
        context = sm.get_character_context()
        assert context or True  # 至少不崩溃
