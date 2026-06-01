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


def _format_source_materials(materials: dict) -> str:
    """将加载的源材料 dict 格式化为 prompt 段落"""
    parts = []
    for name, content in materials.items():
        # 限制单个文件最大长度，避免 prompt 爆炸
        trimmed = content if len(content) <= 20000 else content[:20000] + "\n\n…(后续内容过长，已截断)"
        parts.append(f"### 文件：{name}\n\n{trimmed}")
    return "\n\n---\n\n".join(parts)


def _extract_key_names(materials: dict) -> str:
    """从材料中提取关键专有名词，生成「禁止改名清单」"""
    import re
    # 优先读取角色卡和创作简介文件（最可能包含角色名）
    priority_keys = [k for k in materials if any(
        tag in k.lower() for tag in ['角色', 'roles', '简介', 'intro', '世界观', 'world']
    )]
    target_text = "\n".join(materials[k] for k in priority_keys) if priority_keys else ""
    if not target_text:
        target_text = "\n".join(materials.values())

    found = set()
    # 高精度模式：只匹配明显的角色名称标记
    high_precision = [
        r'name:\s*(\S{1,4})',                    # YAML/prose name: 林风
        r'代表[-—・·]?\s*(\S{1,3})',               # 代表-玄 / 代表「启」
        r'领袖[-—・·]?\s*(\S{1,3})',               # 纯洁派领袖-XX
        r'「([^」\n]{1,3})」\s*[是为]',             # 「启」是方舟内…
        r'名叫\s*[「"]?([^「"\s]{1,3})[」"]?',  # 名叫「璇」
        r'^(?:[\*#]*)\s*(\S{1,3})\s*[：:是为]',   # 玄：黎明方舟首席…
    ]
    for pat in high_precision:
        for m in re.finditer(pat, target_text, re.MULTILINE):
            name = m.group(1).strip().replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
            if re.search(r'[\u4e00-\u9fff]', name) and 1 <= len(name) <= 3:
                if re.search(r'[\d卷章节]', name):
                    continue
                noise_words = {'这是', '一种', '可以', '所以', '但是', '因为', '如果', '虽然', '不过',
                              '其中', '这个', '那个', '第一', '第二', '第三', '一是', '二是',
                              '创作', '简介', '大纲', '核心', '完整', '已有', '故事', '作者','作'}
                if name in noise_words:
                    continue
                # 排除单字且非此类明显角色名
                if len(name) == 1 and name not in ('玄', '启', '璇', '渊'):
                    continue
                found.add(name)

    if not found:
        return ""

    names = sorted(found)
    return (
        "\n\n### 🚫 材料中检测到以下专有名词（角色名/组织名），**必须逐字原样使用，禁止任何改名/翻译/美化/扩展**：\n"
        + "  · " + "  · ".join(names)
        + "\n\n  ⛔ 严格禁止的改名行为示例："
        + "\n     ❌ \"玄\" → \"星炬·弦\"     ❌ \"启\" → \"启明\""
        + "\n     ❌ \"林风\" → \"林峰\"       ❌ \"璇\" → \"晶棺·渊\""
        + "\n  ✅ 正确做法：材料里写什么名，你就用什么名，一字不改。\n"
    )


# ══════════════════════════════════════════════════
# Foundation 文件保存映射
# ══════════════════════════════════════════════════

_FOUNDATION_FILE_MAP = {
    "core_seed": "core_seed.md",
    "character_dynamics": "roles.md",
    "character_state": "character_state.md",
    "world_building": "world_building.md",
    "plot_architecture": "plot_architecture.md",
    "chapter_blueprint": "chapter_blueprint.md",
}


def _save_foundation_file(project_dir: str, output_key: str, content: str):
    """将 checkpoint 输出保存为独立文件，供作者直接查看和修改"""
    import os
    fname = _FOUNDATION_FILE_MAP.get(output_key)
    if fname:
        fpath = os.path.join(project_dir, fname)
        write_file(fpath, content)


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

        # 判断模式：有 source_materials → 忠实转写，否则 → 自由创作
        source_materials = extra.get("source_materials", "")
        if source_materials:
            material_text = _format_source_materials(source_materials)
            name_block = _extract_key_names(source_materials)
            params["mode_instruction"] = (
                "\n## ⚠️ 当前为【忠实转写模式】——你收到的是作者已精心打磨过的完整材料，你的任务是将它们重新组织为 InkEdge 标准格式。\n\n"
                "### 铁律（违反任何一条即为失败）\n"
                "1. **不新增任何设定**：不允许发明材料中没有的角色、势力、地点、物品、事件、规则。\n"
                "2. **不修改已有内容**：所有人物关系、世界观规则、冲突设定、终局方向，保持原样。你可以改措辞使之更散文化，但不能改事实。\n"
                f"3. **不删减核心信息**：材料中出现的每个角色、每条世界观规则、每卷大纲，都要在相应 section 中有所体现。{name_block}\n"
                "4. **缺失的填「待定」**：如果某个 section 在材料中找不到对应内容（如材料没有写 pending_hooks），写「（作者待补充）」而不是自己编。\n\n"
                "### 你的角色\n你是一个高级编辑助理，做的是「格式迁移」和「散文润色」，不是「创意生成」。"
            )
            params["source_section"] = f"\n## 📂 已有创作材料（以下内容优先级高于上方主题描述，一切以此为准）\n\n{material_text}\n"

            prompt = step.format_prompt(**params)
            log.info(f"[Architect] unified — 📋 忠实转写模式 ({len(prompt)} 字符 prompt)")
        else:
            params["mode_instruction"] = (
                "你输出的不是条目化的设定表，而是散文密度的基础骨架——后面写手和规划师能不能写出活人，从这里开始决定。"
            )
            params["source_section"] = ""

            prompt = step.format_prompt(**params)
            log.info(f"[Architect] unified — ✨ 自由创作模式 ({len(prompt)} 字符 prompt)")

        # 注入类型知识（两种模式通用）
        from src.genre_knowledge import KnowledgeLoader
        loader = KnowledgeLoader()
        prompt = loader.inject_to_prompt(
            params.get("genre", ""), prompt, role="architect"
        )

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

    # ══════════════════════════════════════════════════
    # Wizard 模式 — 逐步交互式建书
    # ══════════════════════════════════════════════════

    def wizard_init(self, context: AgentContext) -> dict:
        """初始化交互式建书，返回 wizard state dict"""
        project_dir = context.project_dir
        ensure_dir(project_dir)

        extra = context.extra or {}
        params = {
            "topic": context.user_guidance or extra.get("topic", ""),
            "genre": extra.get("genre", "奇幻"),
            "number_of_chapters": extra.get("num_chapters", 60),
            "word_number": extra.get("word_number", 3000),
            "user_guidance": context.user_guidance or "",
        }

        template_set = self._load_template()
        steps = template_set.get_steps_in_order()
        checkpoint = self._load_checkpoint(project_dir)

        return {
            "params": params,
            "checkpoint": checkpoint,
            "steps": steps,
            "project_dir": project_dir,
            "template_set": template_set,
            "step_feedback": {},  # {step_idx: accumulated feedback text}
            "step_outputs": {},   # {step_idx: last generated output}
        }

    async def wizard_run_step(self, state: dict, step_idx: int, retry: bool = False) -> str:
        """
        运行 wizard 的单个步骤。

        Args:
            state: wizard_init 返回的状态 dict
            step_idx: 步骤索引 (0-based)
            retry: 是否为重试（不跳过已缓存的）

        Returns:
            生成的文本
        """
        steps = state["steps"]
        params = dict(state["params"])
        checkpoint = state["checkpoint"]
        project_dir = state["project_dir"]
        llm = self.get_llm_client()

        step = steps[step_idx]

        # 注入前一步的反馈
        feedback = state["step_feedback"].get(step_idx, "")
        if feedback:
            params["user_feedback"] = (
                f"\n\n## ⚠️ 作者修改意见（必须严格执行）\n{feedback}\n"
            )

        # 如果非重试且已有缓存，跳过
        if not retry and step.output_key and step.output_key in checkpoint:
            return checkpoint[step.output_key]

        step_params = {**params, **checkpoint}
        if step.output_key == "novel_architecture":
            step_params["novel_architecture"] = self._build_novel_architecture(checkpoint)
        elif step.output_key == "chapter_blueprint":
            step_params["novel_architecture"] = self._build_novel_architecture(checkpoint)

        prompt = step.format_prompt(**step_params)
        log.info(f"[Wizard] Step {step.order}: {step.name} ({len(prompt)} 字 prompt)")

        response = await llm.chat_with_retry(prompt)
        output = response.content.strip()

        if step.output_key:
            checkpoint[step.output_key] = output
            self._save_checkpoint(project_dir, checkpoint)

            # 提取角色名（用于后续步骤）
            if step.output_key == "character_dynamics":
                from src.utils.text_utils import extract_character_names
                names = extract_character_names(output)
                if names:
                    checkpoint["character_names"] = names
                    self._save_checkpoint(project_dir, checkpoint)

            # 保存独立文件（供作者直接查看和修改）
            _save_foundation_file(project_dir, step.output_key, output)

        if step.output_file:
            write_file(os.path.join(project_dir, step.output_file), output)

        state["checkpoint"] = checkpoint
        state["step_outputs"][step_idx] = output
        return output

    def wizard_set_feedback(self, state: dict, step_idx: int, feedback: str):
        """为指定步骤追加修改意见"""
        if step_idx not in state["step_feedback"]:
            state["step_feedback"][step_idx] = feedback
        else:
            state["step_feedback"][step_idx] += "\n" + feedback

    def wizard_finalize(self, state: dict) -> str:
        """组装最终输出并保存"""
        project_dir = state["project_dir"]
        checkpoint = state["checkpoint"]
        template_set = state["template_set"]

        # 确保所有 checkpoint 数据都保存为独立文件
        for key, content in checkpoint.items():
            if isinstance(content, str) and len(content) > 50:
                _save_foundation_file(project_dir, key, content)

        novel_setting = self._assemble_final_output(checkpoint, template_set)
        write_file(os.path.join(project_dir, "Novel_setting.txt"), novel_setting)

        log.info(f"[Wizard] ✅ 最终设定已保存至 {project_dir}")
        return novel_setting
