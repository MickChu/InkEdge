"""
ContextBudget — 上下文预算控制器

设计理念（来自 inkOS governed context）：
- LLM 上下文窗口有限，必须精打细算
- 不同类型的内容有不同优先级
- 长篇小说累积上下文巨大，需要智能裁剪
- 支持"证据块"（evidence block）机制：只注入当前章节真正需要的上下文
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import logging

log = logging.getLogger(__name__)

# 默认预算分配（按 token 数估算，1 token ≈ 0.75 中文字）
DEFAULT_BUDGET = {
    "system_prompt": 2000,      # 系统指令
    "story_bible": 6000,        # 小说设定（世界观/规则）
    "current_state": 3000,      # 当前状态（角色状态/全局摘要）
    "ledger": 3000,             # 账本（伏笔/未解决冲突）
    "recent_chapters": 4000,    # 最近章节上下文
    "vector_retrieval": 2000,   # 向量检索召回
    "chapter_blueprint": 1500,  # 章节蓝图（当前+下一章）
    "user_guidance": 1000,      # 用户指导
    "reserved": 1000,           # 预留余量
}
TOTAL_BUDGET = 24000  # 总 token 预算


@dataclass
class ContextBlock:
    """一个上下文块"""
    name: str
    content: str
    priority: int = 5  # 1-10，越高越优先保留
    source: str = ""   # 来源标记（story_bible / vector / user 等）


class ContextBudget:
    """上下文预算管理器"""

    def __init__(self, total_budget: int = TOTAL_BUDGET, budget_map: Optional[dict] = None):
        self.total_budget = total_budget
        self.budget_map = budget_map or DEFAULT_BUDGET.copy()
        self.blocks: List[ContextBlock] = []

    def add_block(self, name: str, content: str, priority: int = 5, source: str = ""):
        """添加上下文块"""
        self.blocks.append(ContextBlock(
            name=name, content=content, priority=priority, source=source
        ))

    def estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数（中文：1 token ≈ 0.75 字）"""
        if not text:
            return 0
        # 中文字符按 0.75 折算，英文按 0.25 折算
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 0.75 + other_chars * 0.25)

    def cap_block(self, content: str, max_tokens: int, truncate_head: bool = False) -> str:
        """
        将文本裁剪到 max_tokens 以内。
        truncate_head=True → 保留尾部（适合最近章节）
        truncate_head=False → 保留头部（适合设定/规则）
        """
        if not content:
            return ""

        current_tokens = self.estimate_tokens(content)
        if current_tokens <= max_tokens:
            return content

        # 按比例截断
        ratio = max_tokens / current_tokens
        target_chars = int(len(content) * ratio)

        if truncate_head:
            return "…(前文省略)…\n" + content[-target_chars:]
        else:
            return content[:target_chars] + "\n…(后文省略)…"

    def build_context_string(self) -> str:
        """
        构建最终注入 LLM 的上下文字符串。
        按预算分配 → 裁剪 → 按优先级排序 → 拼接
        """
        # 计算每个 block 的实际可用预算
        # 未在 budget_map 中注册的 block 平分 remaining
        registered_budget = sum(self.budget_map.values())
        remaining = max(0, self.total_budget - registered_budget)

        unregistered = [b for b in self.blocks if b.source not in self.budget_map]
        unregistered_budget = remaining // max(len(unregistered), 1)

        capped_blocks = []
        total_used = 0

        for block in self.blocks:
            if block.source in self.budget_map:
                cap = self.budget_map[block.source]
            else:
                cap = unregistered_budget

            capped_content = self.cap_block(
                block.content, cap,
                truncate_head=(block.source == "recent_chapters")
            )
            capped_blocks.append((block, capped_content))
            total_used += self.estimate_tokens(capped_content)

        # 按优先级降序排列
        capped_blocks.sort(key=lambda x: x[0].priority, reverse=True)

        # 构建输出
        sections = []
        for block, capped in capped_blocks:
            if capped.strip():
                sections.append(f"## {block.name}\n{capped}")

        log.info(f"[ContextBudget] 总预算 {self.total_budget}, 实际使用 ~{total_used} tokens")
        return "\n\n".join(sections)

    def clear(self):
        """清空所有块"""
        self.blocks.clear()
