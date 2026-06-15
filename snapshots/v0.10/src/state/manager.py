"""
State Manager — 章节写后状态更新

每写完一章后：
1. 保存章节文件 (chapter_N.md)
2. 更新 chapter_summaries.md（追加一句话摘要）
3. 更新 current_state.md（主要角色当前状况）
4. 更新 pending_hooks.md（伏笔状态变更）
"""

import os
import re
import logging
from typing import List, Optional

from src.utils.file_io import write_file, read_file
from .character_state import StateStore
from .tracker import StateTracker, ChapterChanges

log = logging.getLogger(__name__)


class StateManager:
    """小说状态管理器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def save_chapter(self, chapter_number: int, chapter_text: str) -> str:
        """保存章节正文"""
        dir_path = os.path.join(self.project_dir, "chapters")
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, f"chapter_{chapter_number:04d}.md")
        write_file(filepath, chapter_text)
        log.info(f"[StateManager] 第 {chapter_number} 章已保存: {filepath}")
        return filepath

    def auto_summarize(self, chapter_text: str, chapter_number: int) -> str:
        """从正文自动提取一句话摘要（简单规则）"""
        # 取前200字作为摘要基础
        preview = chapter_text[:200].replace("\n", " ")
        # 截断到最后一个句子
        last_period = max(preview.rfind("。"), preview.rfind("！"), preview.rfind("？"))
        if last_period > 20:
            preview = preview[:last_period + 1]
        summary = f"{chapter_number}. {preview}"
        return summary

    def append_summary(self, chapter_number: int, summary: str) -> None:
        """追加章节摘要到 chapter_summaries.md"""
        filepath = os.path.join(self.project_dir, "chapter_summaries.md")
        existing = read_file(filepath, default="")

        # 检查是否已有该章摘要
        existing_lines = existing.strip().split("\n")
        prefix = f"{chapter_number}."
        for line in existing_lines:
            if line.strip().startswith(prefix):
                # 已存在，跳过
                return

        new_line = f"\n{summary}"
        write_file(filepath, existing + new_line)
        log.info(f"[StateManager] 已追加第 {chapter_number} 章摘要")

    def update_hooks(self, chapter_text: str, chapter_number: int,
                     user_hook_notes: Optional[List[str]] = None) -> None:
        """根据用户标注更新伏笔状态"""
        filepath = os.path.join(self.project_dir, "pending_hooks.md")
        hooks_text = read_file(filepath, default="")

        if user_hook_notes:
            # 用户提供了钩子变更，直接追加
            updater = f"\n\n## 第 {chapter_number} 章钩子变更\n"
            for note in user_hook_notes:
                updater += f"- {note}\n"
            write_file(filepath, hooks_text + updater)
            log.info(f"[StateManager] 已更新第 {chapter_number} 章钩子状态")

    def update_current_state(self, chapter_number: int, state_notes: str = "") -> None:
        """更新当前状态（可由 Writer 输出中提取或手动补充）"""
        if not state_notes:
            state_notes = f"第 {chapter_number} 章已完成。"

        filepath = os.path.join(self.project_dir, "current_state.md")
        existing = read_file(filepath, default="")

        entry = f"\n\n## 第 {chapter_number} 章后\n{state_notes}"
        write_file(filepath, existing + entry)
        log.info(f"[StateManager] 已更新当前状态")

    def post_write(self, chapter_number: int, chapter_text: str,
                   hook_notes: Optional[List[str]] = None,
                   state_notes: str = "") -> dict:
        """
        章节写后全流程更新。
        返回保存的文件路径字典。
        """
        # 1. 保存正文
        chapter_path = self.save_chapter(chapter_number, chapter_text)

        # 2. 自动摘要
        summary = self.auto_summarize(chapter_text, chapter_number)
        self.append_summary(chapter_number, summary)

        # 3. 更新状态
        self.update_current_state(chapter_number, state_notes)

        # 4. 更新钩子（如有用户标注）
        if hook_notes:
            self.update_hooks(chapter_text, chapter_number, hook_notes)

        # 5. 更新角色状态（正则回退版，无需 LLM）
        self.track_characters_sync(chapter_text, chapter_number)

        return {
            "chapter_path": chapter_path,
            "summary": summary,
        }

    def track_characters_sync(self, chapter_text: str, chapter_number: int):
        """
        同步更新角色状态（正则回退版）。
        如需 LLM 精度，单独调用 track_characters_async。
        """
        store = StateStore(self.project_dir)
        current = store.load()
        tracker = StateTracker(self.project_dir)
        changes = tracker.extract_changes_sync(chapter_text, chapter_number, current)
        if self._has_changes(changes):
            updated = tracker.apply_changes(current, changes, chapter_number)
            store.save(updated, last_chapter=chapter_number)
            # 每10章保存快照
            if chapter_number % 10 == 0:
                store.snapshot(updated, chapter_number)

    async def track_characters_async(self, chapter_text: str, chapter_number: int,
                                     llm_client):
        """
        异步更新角色状态（LLM 版，更精确）。
        需传入已初始化的 LLM 客户端。
        """
        store = StateStore(self.project_dir)
        current = store.load()
        tracker = StateTracker(self.project_dir)
        changes = await tracker.extract_changes(
            chapter_text, chapter_number, current, llm_client,
        )
        if self._has_changes(changes):
            updated = tracker.apply_changes(current, changes, chapter_number)
            store.save(updated, last_chapter=chapter_number)
            if chapter_number % 10 == 0:
                store.snapshot(updated, chapter_number)

    def _has_changes(self, changes: ChapterChanges) -> bool:
        return bool(
            changes.inventory or changes.abilities or
            changes.relationships or changes.physical_updates or
            changes.location_updates
        )

    def get_character_context(self, max_chars: int = 1500) -> str:
        """获取角色状态摘要（供 ContextBuilder 使用）"""
        store = StateStore(self.project_dir)
        chars = store.load()
        tracker = StateTracker(self.project_dir)
        return tracker.format_for_context(chars, max_chars=max_chars)

    async def settle_async(self, chapter_text: str, chapter_number: int,
                           llm_client, chapter_count: int = 0,
                           volume_outline: str = ""):
        """
        异步结算（LLM 版：Observer + 3 Settlers）。
        需传入已初始化的 LLM 客户端。
        """
        from src.settlement import SettlementOrchestrator
        orch = SettlementOrchestrator(self.project_dir)
        return await orch.settle(
            chapter_text, chapter_number, llm_client,
            chapter_count, volume_outline,
        )
