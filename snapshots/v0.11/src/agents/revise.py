# -*- coding: utf-8 -*-
"""
revise.py — ReviseAgent

加载已写章节, 根据 guidance 改写。
策略: 保留原版为 .bak, 新版本覆盖原文件。
"""

import os
import logging
from pathlib import Path
from typing import Optional

from src.core.base_agent import BaseAgent, AgentContext, AgentResult
from src.utils.llm_client import LLMClient
from src.utils.config import get_config

log = logging.getLogger("inkedge.revise")


class ReviseAgent(BaseAgent):
    """章节改写 Agent"""

    def __init__(self):
        self.llm = LLMClient()
        self.config = get_config().all()

    async def safe_run(self, context: AgentContext) -> AgentResult:
        project_dir = context.project_dir
        chapter_num = context.extra.get("chapter_number", 1)
        guidance = context.user_guidance or ""
        word_count = context.extra.get("word_count", 3000)

        # ── 加载原章节 ──
        chapter_path = self._find_chapter(project_dir, chapter_num)
        if not chapter_path:
            return AgentResult(
                success=False,
                error=f"第 {chapter_num} 章不存在: {project_dir}/chapters/",
            )

        original_text = open(chapter_path, "r", encoding="utf-8").read()

        # ── 组装改写上下文 ──
        context_text = self._build_context(project_dir, original_text, guidance)

        # ── 生成改写 ──
        log.info(f"✏️ 改写第 {chapter_num} 章 (原 {len(original_text)} 字)")
        if guidance:
            log.info(f"   指导: {guidance}")

        system = (
            "你是一位专业的小说家。请根据指导，改写以下章节。\n\n"
            "要求：\n"
            "- 保持故事设定、角色关系、核心情节不变\n"
            "- 根据「修改指导」调整文笔、节奏、信息密度\n"
            "- 保持原文风格和叙事视角\n"
            "- 输出完整改写后的章节正文"
        )

        try:
            response = await self.llm.chat(
                system=system,
                prompt=context_text,
                max_tokens=self.config.get("max_tokens", 8192),
                temperature=0.8,
            )
            revised_text = response.content.strip()
        except Exception as e:
            return AgentResult(success=False, error=f"LLM 调用失败: {e}")

        if not revised_text:
            return AgentResult(success=False, error="LLM 返回空内容")

        # ── 备份原版 ──
        bak_path = str(chapter_path) + ".bak"
        open(bak_path, "w", encoding="utf-8").write(original_text)
        log.info(f"   📦 原版备份: {os.path.basename(bak_path)}")

        # ── 写入新版 ──
        open(chapter_path, "w", encoding="utf-8").write(revised_text)
        log.info(f"   ✅ 改写完成 ({len(original_text)} → {len(revised_text)} 字)")

        return AgentResult(
            success=True,
            context_updates={
                "chapter_text": revised_text,
                "chapter_number": chapter_num,
                "original_length": len(original_text),
                "revised_length": len(revised_text),
                "bak_path": bak_path,
                "chapter_path": chapter_path,
            },
        )

    # ============================================================
    # 辅助方法
    # ============================================================

    def _find_chapter(self, project_dir: str, num: int) -> Optional[str]:
        """查找章节文件（兼容多种命名格式）"""
        ch_dir = os.path.join(project_dir, "chapters")
        if not os.path.exists(ch_dir):
            return None

        # 标准命名: chapter_0001.md
        candidates = [
            f"chapter_{num:04d}.md",
            f"chapter_{num:04d}.txt",
            f"chapter_{num}.md",
            f"chapter_{num}.txt",
        ]

        for c in candidates:
            p = os.path.join(ch_dir, c)
            if os.path.exists(p):
                return p

        # 模糊匹配（中文命名如 0001_迭代 V2.md）
        for fname in sorted(os.listdir(ch_dir)):
            if fname.startswith(f"{num:04d}") and fname.endswith((".md", ".txt")):
                return os.path.join(ch_dir, fname)

        return None

    def _build_context(self, project_dir: str, chapter_text: str,
                       guidance: str) -> str:
        """组装改写上下文"""
        parts = []
        base = Path(project_dir)

        # 1. 书籍设定
        for fname in ["story_frame.md", "book_rules.md", "Novel_setting.txt"]:
            for d in [base, base / "foundation", base / "story"]:
                fp = d / fname
                if fp.exists():
                    text = fp.read_text(encoding="utf-8").strip()
                    if text:
                        parts.append(f"## 书籍设定 ({fname})\n{text}")
                    break

        # 2. 角色档案
        for d in [base, base / "foundation", base / "story"]:
            fp = d / "roles.md"
            if fp.exists():
                text = fp.read_text(encoding="utf-8").strip()
                if text:
                    parts.append(f"## 角色档案\n{text}")
                break

        # 3. 风格指南
        fp = base / "style_guide.md"
        if fp.exists():
            text = fp.read_text(encoding="utf-8").strip()
            if text:
                parts.append(f"## 风格指南\n{text}")

        # 4. 当前章节 + 修改指导
        parts.append("## 原章节正文")
        parts.append(chapter_text)
        parts.append(f"\n## 修改指导\n{guidance or '优化文笔和节奏，增强可读性'}")
        parts.append("\n请输出完整改写后的章节正文（不包含上述背景信息）。")

        return "\n\n".join(parts)
