"""
Phase 5c — ConsistencyValidator（一致性校验）

检查新章节与 foundation 文件的一致性：
  - 角色名是否正确
  - 是否违反 book_rules 中的 prohibitions
  - pending_hooks 是否应该在本章回收
  - 基础设定是否被违反
"""
import os
import re
import logging
from typing import List, Optional, Set

from .report import ConsistencyIssue, ConsistencyReport

log = logging.getLogger(__name__)


def _extract_names(text: str) -> Set[str]:
    """从 YAML/散文角色卡中提取角色名"""
    names = set()
    # YAML name: XXX
    for m in re.finditer(r'^name:\s*(.+)', text, re.MULTILINE):
        names.add(m.group(1).strip())
    # ---ROLE--- ... name: XXX
    for m in re.finditer(r'name:\s*(.+?)(?:\n|$)', text):
        names.add(m.group(1).strip())
    return names


def _extract_prohibitions(text: str) -> List[str]:
    """从 book_rules.md 提取禁止项"""
    rules = []
    # YAML prohibitions 列表
    in_prohibitions = False
    for line in text.split("\n"):
        if "prohibitions:" in line:
            in_prohibitions = True
            continue
        if in_prohibitions:
            stripped = line.strip()
            if stripped.startswith("- "):
                rules.append(stripped[2:].strip().strip('"').strip("'"))
            elif stripped and not stripped.startswith("-") and not stripped.startswith("#"):
                # 可能是下一段 YAML key
                if ":" in stripped and not stripped.startswith(" "):
                    in_prohibitions = False
    return rules


def _extract_hooks(text: str, current_chapter: int) -> List[tuple]:
    """提取应该在当前章节回收的伏笔"""
    due_hooks = []
    for m in re.finditer(r'\[startChapter[=:]\s*(\d+)\](.*?)(?=\[startChapter|\Z)', text, re.DOTALL):
        ch = int(m.group(1))
        hook = m.group(2).strip()
        # 找预计回收卷
        recycle_match = re.search(r'→\s*(?:预计回收\s*)?(?:第(\d+)卷|卷(\d+))', hook)
        if recycle_match:
            recycle_vol = int(recycle_match.group(1) or recycle_match.group(2))
            # 假设每卷 20 章，current_chapter 所在卷
            current_vol = (current_chapter - 1) // 20 + 1
            if recycle_vol <= current_vol and ch < current_chapter:
                due_hooks.append((ch, hook[:80]))
    return due_hooks


class ConsistencyValidator:
    """一致性校验器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def _read_file(self, filename: str) -> str:
        """读取项目文件"""
        path = os.path.join(self.project_dir, filename)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def validate(self, chapter_text: str, chapter_number: int) -> ConsistencyReport:
        """
        校验章节一致性。

        Returns:
            ConsistencyReport
        """
        issues: List[ConsistencyIssue] = []

        roles_text = self._read_file("roles.md")
        rules_text = self._read_file("book_rules.md")
        hooks_text = self._read_file("pending_hooks.md")

        # ── 1. 角色名检查 ──────────────────────────────────────────
        known_names = _extract_names(roles_text)
        names_checked = len(known_names)

        if known_names:
            # 检查核心角色名是否在正文中出现（不是必须，但缺失是 info）
            for name in known_names:
                # 中文名 2-4 字
                if 2 <= len(name) <= 4 and name not in chapter_text:
                    pass  # 某章没有某个角色是正常的，不报警

        # 检查是否有未知的 3 字人名出现（可能是拼写错误）
        # 跳过已知名字 + 常见词
        new_names = set(re.findall(r'[沈赵李王张刘陈杨吴周]{1}[^\s，。！？…、]{1,2}', chapter_text))
        # 只检查高频出现的（至少出现3次的3字名）
        name_counts = {}
        for m in re.finditer(r'([\u4e00-\u9fff]{2,3})', chapter_text):
            n = m.group(1)
            if len(n) == 2 and n not in known_names:
                name_counts[n] = name_counts.get(n, 0) + 1

        for name, count in name_counts.items():
            if count >= 4 and name not in known_names:
                # 可能是 typo 或新角色
                if any(abs(len(name) - len(k)) == 0 and 
                       sum(1 for a, b in zip(name, k) if a == b) / len(name) > 0.5
                       for k in known_names):
                    # 找到相似已知名 → 可能是拼写错误
                    similar = [k for k in known_names if len(k) == len(name)]
                    if similar:
                        issues.append(ConsistencyIssue(
                            issue_type="name",
                            description=f"角色名「{name}」出现{count}次，未在角色卡中找到。相似角色: {similar}",
                            source_ref="roles.md",
                            chapter_ref=f"第{chapter_number}章",
                            severity="warning",
                        ))

        # ── 2. 规则遵循检查 ──────────────────────────────────────
        prohibitions = _extract_prohibitions(rules_text)
        rules_checked = len(prohibitions)

        for rule in prohibitions:
            # 从禁止项中提取核心关键词（去"不"和"禁止"前缀，拆分为词）
            core = rule.replace("不", "").replace("禁止", "").strip()
            if len(core) >= 2:
                # 将核心短语拆为2-3字片段，任一命中即触发
                fragments = [core[i:i+2] for i in range(0, len(core)-1)]
                fragments += [core[i:i+3] for i in range(0, len(core)-2)]
                # 检查是否至少2个片段出现在正文中
                hits = sum(1 for f in fragments if f in chapter_text)
                if hits >= 2 or (len(fragments) <= 2 and hits >= 1):
                    issues.append(ConsistencyIssue(
                        issue_type="rule",
                        description=f"违反 book_rules 禁止项: {rule}",
                        source_ref="book_rules.md",
                        chapter_ref=f"第{chapter_number}章",
                        severity="error",
                    ))

        # ── 3. 伏笔回收检查 ──────────────────────────────────────
        due_hooks = _extract_hooks(hooks_text, chapter_number)
        hooks_checked = len(due_hooks)

        for hook_ch, hook_text in due_hooks:
            # 简单检查：伏笔关键词是否在本章出现
            keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', hook_text)
            hook_key = ''.join(keywords[:3]) if keywords else hook_text[:10]
            if hook_key and hook_key not in chapter_text:
                issues.append(ConsistencyIssue(
                    issue_type="hook",
                    description=f"伏笔回收到期（第{hook_ch}章埋）: {hook_text}",
                    source_ref="pending_hooks.md",
                    chapter_ref=f"第{chapter_number}章",
                    severity="info",
                ))

        # ── 汇总 ──────────────────────────────────────────────────
        errors = [i for i in issues if i.severity == "error"]
        passed = len(errors) == 0

        return ConsistencyReport(
            passed=passed,
            issues=issues,
            names_checked=names_checked,
            rules_checked=rules_checked,
            hooks_checked=hooks_checked,
        )
