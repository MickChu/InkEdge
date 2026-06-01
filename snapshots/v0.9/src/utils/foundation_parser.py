"""
unified_foundation — 统一基础设定解析器

解析 Architect 输出的 === SECTION: name === 分块格式，
提取各 section 保存为独立文件。
"""

import os
import re
import logging
from typing import Dict

log = logging.getLogger(__name__)

# SECTION 名称 → 输出文件名
SECTION_FILE_MAP = {
    "story_frame": "story_frame.md",
    "volume_map": "volume_map.md",
    "roles": "roles.md",
    "book_rules": "book_rules.md",
    "pending_hooks": "pending_hooks.md",
}


def parse_sections(raw_text: str) -> Dict[str, str]:
    """
    解析 === SECTION: name === 格式的文本，提取各 section 内容。

    返回 dict: {section_name: content}
    """
    sections = {}
    # 匹配 === SECTION: xxx === ... === SECTION: 或文本末尾
    pattern = r'=== SECTION:\s*(\S+)\s*===\s*\n(.*?)(?=\n=== SECTION:|\Z)'
    for match in re.finditer(pattern, raw_text, re.DOTALL):
        name = match.group(1)
        content = match.group(2).strip()
        sections[name] = content

    if not sections:
        log.warning("unified output 中未找到任何 === SECTION: === 标记")
        return {}

    log.info(f"解析到 {len(sections)} 个 section: {list(sections.keys())}")
    return sections


def save_sections(sections: Dict[str, str], output_dir: str) -> Dict[str, str]:
    """
    将各个 section 保存为独立文件。

    返回: {section_name: file_path}
    """
    saved = {}
    for name, content in sections.items():
        filename = SECTION_FILE_MAP.get(name, f"{name}.md")
        filepath = os.path.join(output_dir, filename)
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else output_dir, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        saved[name] = filepath
        log.info(f"  {name} → {filepath} ({len(content)} 字)")

    return saved


def extract_world_building_from_story_frame(story_frame: str) -> str:
    """
    从 story_frame 中提取世界观段落（段 3）。

    使用简单的段落分割逻辑：找到 "### 段 3：世界观" 或 "段 3" 到下一个 "###" 的内容。
    """
    # 尝试匹配 "### 段 3" 到下一个 ### 标题
    pattern = r'(?:###?\s*)?段\s*3[：:]\s*世界观.*?\n(.*?)(?=\n###?\s*段\s*4|\Z)'
    match = re.search(pattern, story_frame, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 备选：返回整个 story_frame 的前 1/3
    log.warning("无法精确定位世界观段落，返回 story_frame 全段")
    return story_frame
