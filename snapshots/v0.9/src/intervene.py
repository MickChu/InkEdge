"""
intervene — 定向修改 foundation 文件

支持的操作：
  - list: 列出可干预的文件及摘要
  - add: 追加内容（hooks / rules 新增条目）
  - update: 替换角色卡 / story_frame 段落
  - remove: 删除特定条目（伏笔 / 规则）
"""

import os
import re
import logging
from typing import Optional

from src.utils.file_io import read_file, write_file

log = logging.getLogger(__name__)

FOUNDATION_FILES = [
    "story_frame.md",
    "volume_map.md",
    "roles.md",
    "book_rules.md",
    "pending_hooks.md",
]


def get_project_path(name: str) -> str:
    """获取项目目录"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "projects", name)


def list_files(project_dir: str) -> dict:
    """列出可干预的文件及其状态"""
    result = {}
    for fname in FOUNDATION_FILES:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            content = read_file(fpath)
            result[fname] = {
                "exists": True,
                "size": len(content),
                "preview": content[:120].replace("\n", " ") + "…",
            }
        else:
            result[fname] = {"exists": False, "size": 0, "preview": "(未生成)"}
    return result


# ══════════════════════════════════════════════════
# 通用操作
# ══════════════════════════════════════════════════

def _append_to_file(fpath: str, new_content: str, sep: str = "\n") -> str:
    """追加内容到文件末尾，返回变更摘要"""
    old = read_file(fpath)
    if not old:
        return f"文件 {fpath} 不存在，无法追加"

    new_text = old.rstrip() + sep + new_content.strip() + "\n"
    write_file(fpath, new_text)
    return f"已追加 {len(new_content)} 字到 {os.path.basename(fpath)}"


def _remove_line(fpath: str, pattern: str) -> str:
    """按正则模式删除行，返回删除的行数"""
    old = read_file(fpath)
    if not old:
        return f"文件 {fpath} 不存在"

    lines = old.split("\n")
    new_lines = [ln for ln in lines if not re.search(pattern, ln)]
    removed = len(lines) - len(new_lines)
    if removed == 0:
        return "未找到匹配内容，无变更"

    write_file(fpath, "\n".join(new_lines) + "\n")
    return f"已删除 {removed} 行"


# ══════════════════════════════════════════════════
# story_frame.md — 按段号替换
# ══════════════════════════════════════════════════

def update_story_frame_segment(project_dir: str, segment: int, new_content: str) -> str:
    """替换 story_frame 的第 N 段"""
    fpath = os.path.join(project_dir, "story_frame.md")
    old = read_file(fpath)
    if not old:
        return "story_frame.md 不存在"

    pattern = rf"(### 段 {segment}[：:].*?)(\n### 段|\n---|\Z)"
    match = re.search(pattern, old, re.DOTALL)
    if not match:
        return f"未找到「段 {segment}」"

    # 提取段标题
    header = re.search(rf"(### 段 {segment}[：:].*?\n)", old)
    if not header:
        return f"未找到「段 {segment}」标题"

    replacement = header.group(1).rstrip() + "\n\n" + new_content.strip() + "\n"
    new_text = old[: match.start()] + replacement + old[match.end():]
    write_file(fpath, new_text)
    return f"story_frame 段 {segment} 已更新 ({len(new_content)} 字)"


# ══════════════════════════════════════════════════
# roles.md — 按角色名更新
# ══════════════════════════════════════════════════

def update_role(project_dir: str, character: str, new_content: str) -> str:
    """替换 roles 中指定角色的 ---CONTENT--- 部分"""
    fpath = os.path.join(project_dir, "roles.md")
    old = read_file(fpath)
    if not old:
        return "roles.md 不存在"

    # 匹配指定角色块
    pattern = rf"---ROLE---\s*\ntier:.*?\nname:\s*{re.escape(character)}\s*\n---CONTENT---\s*\n(.*?)(\n---ROLE---|\n---\s*\n|\Z)"
    match = re.search(pattern, old, re.DOTALL | re.IGNORECASE)
    if not match:
        return f"未找到角色「{character}」"

    # 重建角色块
    before = old[: match.start()]
    after = old[match.end():]
    header_match = re.search(
        rf"(---ROLE---\s*\n(?:tier:.*?\n)?name:\s*{re.escape(character)}\s*\n---CONTENT---\s*\n)",
        old, re.DOTALL | re.IGNORECASE,
    )
    if not header_match:
        return f"角色「{character}」格式异常"

    replacement = header_match.group(1).rstrip() + "\n" + new_content.strip() + "\n"
    new_text = before + replacement + after
    write_file(fpath, new_text)
    return f"角色「{character}」已更新 ({len(new_content)} 字)"


# ══════════════════════════════════════════════════
# book_rules.md — 增删 prohibited items
# ══════════════════════════════════════════════════

def add_prohibition(project_dir: str, rule: str) -> str:
    """在 book_rules 的 prohibitions 列表中添加一条"""
    fpath = os.path.join(project_dir, "book_rules.md")
    old = read_file(fpath)
    if not old:
        return "book_rules.md 不存在"

    # 找到 prohibitions: 列表末尾
    match = re.search(r"(prohibitions:\s*\[[^\]]*\])", old, re.DOTALL)
    if not match:
        # 没有 prohibitions 字段？追加到文件末尾
        new_line = f"\n# 追加规则\nprohibitions:\n  - {rule}\n"
        write_file(fpath, old.rstrip() + new_line)
        return f"新增规则: {rule}"

    block = match.group(1)
    # 在 ] 之前插入新条目
    new_block = block.replace("]", f", {rule}]") if block.endswith("]") else block + f"\n  - {rule}\n"
    new_text = old[: match.start()] + new_block + old[match.end():]
    write_file(fpath, new_text)
    return f"已添加禁止规则: {rule}"


def remove_prohibition(project_dir: str, pattern: str) -> str:
    """从 book_rules 中删除匹配的 prohibition"""
    fpath = os.path.join(project_dir, "book_rules.md")
    old = read_file(fpath)
    if not old:
        return "book_rules.md 不存在"

    match = re.search(r"(prohibitions:\s*\[)([^\]]*)(\])", old, re.DOTALL)
    if not match:
        return "未找到 prohibitions 字段"

    items_raw = match.group(2)
    # 按逗号分割并去除引号
    items = [it.strip().strip("'\"") for it in items_raw.split(",") if it.strip()]
    new_items = [it for it in items if not re.search(pattern, it)]

    if len(new_items) == len(items):
        return f"未找到匹配「{pattern}」的规则"

    new_list = ", ".join(new_items)
    new_text = old[: match.start(2)] + new_list + old[match.end(2):]
    write_file(fpath, new_text)
    return f"已删除 {len(items) - len(new_items)} 条规则"


# ══════════════════════════════════════════════════
# pending_hooks.md — 增删伏笔
# ══════════════════════════════════════════════════

def add_hook(project_dir: str, hook: str) -> str:
    """追加一条伏笔"""
    fpath = os.path.join(project_dir, "pending_hooks.md")
    return _append_to_file(fpath, hook)


def remove_hook(project_dir: str, pattern: str) -> str:
    """删除匹配的伏笔行"""
    fpath = os.path.join(project_dir, "pending_hooks.md")
    return _remove_line(fpath, pattern)


# ══════════════════════════════════════════════════
# volume_map.md — 追加
# ══════════════════════════════════════════════════

def append_volume_map(project_dir: str, content: str) -> str:
    """追加卷纲内容"""
    fpath = os.path.join(project_dir, "volume_map.md")
    return _append_to_file(fpath, content, sep="\n\n")
