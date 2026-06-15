"""
text_utils — 文本处理工具
"""

import re


def count_chinese_chars(text: str) -> int:
    """统计中文字符数"""
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def estimate_tokens(text: str) -> int:
    """
    粗略估算 token 数。
    中文：1 token ≈ 0.75 中文字
    英文：1 token ≈ 4 字符
    """
    if not text:
        return 0
    chinese = count_chinese_chars(text)
    other = len(text) - chinese
    return int(chinese * 0.75 + other * 0.25)


def extract_between(text: str, start_marker: str, end_marker: str) -> str:
    """提取两个标记之间的文本"""
    try:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker, start)
        return text[start:end].strip()
    except ValueError:
        return ""


def truncate_text(text: str, max_chars: int, ellipsis: str = "…") -> str:
    """截断文本到指定字符数"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(ellipsis)] + ellipsis


def split_paragraphs(text: str) -> list[str]:
    """按空行分割段落"""
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


def clean_response(text: str) -> str:
    """
    清洗 LLM 响应中常见的前缀/后缀噪音：
    - 移除 markdown 代码块包裹
    - 移除 "好的，以下是..." 开头
    - 移除末尾的 "希望你喜欢..."
    """
    # 移除 ```...``` 包裹
    text = re.sub(r'^```[a-z]*\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)

    # 移除常见的废话前缀
    prefixes = [
        r'^(好的[，,]\s*以下是.*?[：:]\s*\n?)',
        r'^(以下是.*?[：:]\s*\n?)',
        r'^(根据你的要求[，,]\s*.*?[：:]\s*\n?)',
    ]
    for pattern in prefixes:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # 移除常见的废话后缀
    suffixes = [
        r'\n*(希望.*?喜欢.*?[。！])$',
        r'\n*(如果.*?请告诉我.*?[。！])$',
    ]
    for pattern in suffixes:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    return text.strip()


def extract_character_names(text: str) -> str:
    """
    从角色设定文本中提取角色名列表。
    匹配模式：## 角色N：名称 或 【名称】 或 - **姓名**：名称
    返回逗号分隔的角色名，供后续步骤做一致性约束。
    """
    names = []

    # 模式1: ## 角色一：沈墨
    for m in re.finditer(r'##\s*角色[\d一二三四五六七八九十]+[：:]\s*(\S+)', text):
        name = m.group(1)
        # 截断到第一个标点/符号：沈墨——逆命书生 → 沈墨
        name = re.split(r'[（(——\-—,，、。；;]', name)[0].strip()
        if name and len(name) <= 4:
            names.append(name)

    # 模式2: 【沈墨】
    for m in re.finditer(r'【(.+?)】', text):
        name = m.group(1)
        name = re.split(r'[（(——\-—,，、。；;]', name)[0].strip()
        if len(name) <= 4 and name and not any(kw in name for kw in ['章', '物品', '能力', '状态', '关系', '经历', '事件']):
            if name not in names:
                names.append(name)

    # 模式3: **姓名**：沈墨
    for m in re.finditer(r'\*\*姓名\*\*[：:]\s*(\S+)', text):
        name = m.group(1)
        name = re.split(r'[，,、。；;（(]', name)[0].strip()
        if name and len(name) <= 4 and name not in names:
            names.append(name)

    return "、".join(dict.fromkeys(names[:8]))  # 去重，最多8个角色
