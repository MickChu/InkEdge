"""
ArchitectAgent — 小说架构师

负责生成小说的完整基础设定。支持两种模式：
  - unified（默认）：一次 LLM 调用输出全部 5 段（story_frame / volume_map /
    roles / book_rules / pending_hooks），世界观融入 story_frame。inkOS 风格。
  - snowflake：6 步分步生成，每步有独立的 checkpoint 和输出。
"""

import json
import os
import logging
from typing import Optional

from src.core.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResult
from src.prompts.base_template import PromptTemplateSet, TemplateStep
from src.utils.file_io import write_file, read_file, ensure_dir
from src.utils.foundation_parser import parse_sections, save_sections

log = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """小说架构师 Agent"""

    def __init__(self, template_name: str = "unified", config: Optional[AgentConfig] = None):
        super().__init__(config)
        self.template_name = template_name
        self._template_set: Optional[PromptTemplateSet] = None

    @property
    def agent_name(self) -> str:
        return "Architect"

    def _load_template(self) -> PromptTemplateSet:
        if self._template_set is None:
            from src.prompts import get_template_registry
            registry = get_template_registry()
            template_set = registry.get(self.template_name)
            if template_set is None:
                available = registry.list()
                raise ValueError(
                    f"模板集 '{self.template_name}' 不存在。可用: {available}"
                )
            self._template_set = template_set
        return self._template_set

    async def run(self, context: AgentContext) -> AgentResult:
        """执行建书流程"""
        if self.template_name == "unified":
            return await self._run_unified(context)
        else:
            return await self._run_snowflake(context)

    # ══════════════════════════════════════════════════
    # Unified 模式 — 一次调用输出完整 foundation
    # ══════════════════════════════════════════════════

    async def _run_unified(self, context: AgentContext) -> AgentResult:
        project_dir = context.project_dir
        ensure_dir(project_dir)
        llm = self.get_llm_client()

        template_set = self._load_template()
        step = template_set.get_step(1)

        extra = context.extra or {}
        params = {
            "topic": context.user_guidance or extra.get("topic", ""),
            "genre": extra.get("genre", "奇幻"),
            "number_of_chapters": extra.get("num_chapters", 60),
            "word_number": extra.get("word_number", 3000),
            "user_guidance": context.user_guidance or "",
        }

        prompt = step.format_prompt(**params)
        
        # 注入类型知识
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        prompt = loader.inject_to_prompt(
            params.get("genre", ""), prompt, role="architect"
        )

        log.info(f"[Architect] unified 模式 — 生成完整 foundation ({len(prompt)} 字符 prompt)")

        response = await llm.chat_with_retry(prompt, max_tokens=8192)
        raw_output = response.content

        if not raw_output or len(raw_output) < 500:
            return AgentResult(success=False, error="LLM 返回空或过短响应")

        log.info(f"[Architect] 收到 {len(raw_output)} 字响应，开始解析 section...")

        # 解析 === SECTION: === 标记
        sections = parse_sections(raw_output)

        if not sections:
            # 回退：保存原始输出供人工检查
            raw_path = os.path.join(project_dir, "_raw_output.md")
            write_file(raw_path, raw_output)
            return AgentResult(
                success=False,
                error=f"无法解析 section 格式，原始输出已保存至 {raw_path}"
            )

        # 保存各 section
        saved = save_sections(sections, project_dir)

        # 生成兼容的 Novel_setting.txt（供 status 等命令读取）
        novel_setting = self._assemble_novel_setting(sections)
        write_file(os.path.join(project_dir, "Novel_setting.txt"), novel_setting)

        # 保存断点
        checkpoint = {**sections}
        self._save_checkpoint(project_dir, checkpoint)

        log.info(f"[Architect] ✅ unified 建书完成 — 5 段已保存至 {project_dir}")

        return AgentResult(
            success=True,
            context_updates={
                "foundation": novel_setting,
                "story_frame": sections.get("story_frame", ""),
                "volume_map": sections.get("volume_map", ""),
                "roles": sections.get("roles", ""),
            },
        )

    def _assemble_novel_setting(self, sections: dict) -> str:
        """将 unified sections 组装为兼容格式的 Novel_setting.txt"""
        parts = ["# 小说设定"]

        if "story_frame" in sections:
            parts.append(f"\n## 故事框架\n{sections['story_frame']}")
        if "roles" in sections:
            parts.append(f"\n## 角色设定\n{sections['roles']}")
        if "book_rules" in sections:
            parts.append(f"\n## 创作规则\n{sections['book_rules']}")
        if "pending_hooks" in sections:
            parts.append(f"\n## 初始伏笔\n{sections['pending_hooks']}")

        return "\n".join(parts)

    # ══════════════════════════════════════════════════
    # Snowflake 模式 — 6 步分步生成（兼容旧版）
    # ══════════════════════════════════════════════════

    async def _run_snowflake(self, context: AgentContext) -> AgentResult:
        project_dir = context.project_dir
        ensure_dir(project_dir)
        llm = self.get_llm_client()

        template_set = self._load_template()
        steps = template_set.get_steps_in_order()

        extra = context.extra or {}
        topic = context.user_guidance or extra.get("topic", "")
        genre = extra.get("genre", "奇幻")
        num_chapters = extra.get("num_chapters", 60)
        word_number = extra.get("word_number", 3000)

        log.info(f"[Architect] snowflake 模式: {template_set.display_name} v{template_set.version}")
        log.info(f"[Architect] 共 {len(steps)} 个步骤")

        params = {
            "topic": topic, "genre": genre,
            "number_of_chapters": num_chapters, "word_number": word_number,
            "user_guidance": context.user_guidance or "",
        }

        checkpoint = self._load_checkpoint(project_dir)

        for step in steps:
            if step.output_key and step.output_key in checkpoint:
                log.info(f"[Architect] Step {step.order}: {step.name} (已缓存)")
                continue

            log.info(f"[Architect] Step {step.order}: {step.name} — {step.description}")

            step_params = {**params, **checkpoint}
            if step.output_key == "novel_architecture":
                step_params["novel_architecture"] = self._build_novel_architecture(checkpoint)
            elif step.output_key == "chapter_blueprint":
                step_params["novel_architecture"] = self._build_novel_architecture(checkpoint)

            try:
                prompt = step.format_prompt(**step_params)
            except ValueError as e:
                log.warning(f"[Architect] 参数不足: {e}")
                continue

            response = await llm.chat_with_retry(prompt)
            output = response.content.strip()

            if not output and step.required_params:
                return AgentResult(success=False, error=f"Step {step.order} 空响应")

            log.info(f"[Architect] Step {step.order} 完成 ({len(output)} 字)")

            if step.output_key:
                checkpoint[step.output_key] = output
                self._save_checkpoint(project_dir, checkpoint)

                if step.output_key == "character_dynamics":
                    from src.utils.text_utils import extract_character_names
                    names = extract_character_names(output)
                    if names:
                        checkpoint["character_names"] = names
                        self._save_checkpoint(project_dir, checkpoint)
                        log.info(f"[Architect] 提取角色名: {names}")

            if step.output_file:
                write_file(os.path.join(project_dir, step.output_file), output)

        novel_setting = self._assemble_final_output(checkpoint, template_set)
        write_file(os.path.join(project_dir, "Novel_setting.txt"), novel_setting)

        log.info(f"[Architect] ✅ snowflake 建书完成")

        return AgentResult(
            success=True,
            context_updates={
                "foundation": novel_setting,
                "chapter_blueprint": checkpoint.get("chapter_blueprint", ""),
                "character_state": checkpoint.get("character_state", ""),
            },
        )

    def _build_novel_architecture(self, checkpoint: dict) -> str:
        parts = []
        for key, label in [("core_seed", "核心种子"), ("character_dynamics", "角色动力学"),
                           ("world_building", "世界观"), ("plot_architecture", "情节架构")]:
            if key in checkpoint:
                parts.append(f"## {label}\n{checkpoint[key]}")
        return "\n\n".join(parts)

    def _assemble_final_output(self, checkpoint: dict, template_set):
        sections = ["# 小说设定"]
        label_map = {
            "core_seed": ("一、核心种子", None),
            "character_dynamics": ("二、角色动力学", None),
            "world_building": ("三、世界观", None),
            "plot_architecture": ("四、情节架构", None),
        }
        for key, (label, _) in label_map.items():
            if key in checkpoint:
                sections.append(f"\n## {label}\n{checkpoint[key]}")
        return "\n".join(sections)

    def _load_checkpoint(self, project_dir: str) -> dict:
        path = os.path.join(project_dir, "partial_architecture.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_checkpoint(self, project_dir: str, data: dict) -> None:
        path = os.path.join(project_dir, "partial_architecture.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
