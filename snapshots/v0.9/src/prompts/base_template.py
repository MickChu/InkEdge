"""
PromptTemplate — 提示词模板规则系统

设计目标：
- 每套写作方法论是一个 TemplateSet（如雪花写作法、英雄之旅、Save the Cat）
- 每个 TemplateSet 包含多个 Step（按顺序执行的 LLM 调用）
- 每个 Step 定义自己的 prompt 模板、所需参数、输出键
- TemplateRegistry 统一管理所有模板集，ArchitectAgent 只需按名称加载

添加新模板只需：
1. 在 prompts/ 下新建目录（如 prompts/heros_journey/）
2. 每个 Step 一个 .py 文件
3. 在 __init__.py 中注册
"""

import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

log = logging.getLogger(__name__)


@dataclass
class TemplateStep:
    """模板中的一个步骤"""
    # 步骤序号（支持浮点，如 2.5 表示插在 2 和 3 之间）
    order: float
    # 步骤名称（如 "核心种子"）
    name: str
    # 步骤描述
    description: str = ""
    # 提示词模板字符串，支持 {param} 占位符
    prompt: str = ""
    # 必须提供的参数列表
    required_params: List[str] = field(default_factory=list)
    # 可选参数
    optional_params: List[str] = field(default_factory=list)
    # 输出在 checkpoint 中的键名
    output_key: str = ""
    # 是否生成独立输出文件（如 character_state.txt）
    output_file: Optional[str] = None
    # 后处理函数（可选，如组装多个 step 的输出）
    post_process: Optional[Callable] = None

    def format_prompt(self, **kwargs) -> str:
        """用参数填充模板"""
        # 检查必填参数
        missing = [p for p in self.required_params if p not in kwargs]
        if missing:
            raise ValueError(f"Step '{self.name}' 缺少必填参数: {missing}")
        # 填充（安全模式：未提供的可选参数保留占位符）
        return self.prompt.format(**kwargs)


@dataclass
class PromptTemplateSet:
    """一套完整的提示词模板集"""
    # 模板集唯一标识
    name: str
    # 显示名称
    display_name: str
    # 版本
    version: str = "1.0"
    # 描述
    description: str = ""
    # 适用类型（如 ["奇幻", "科幻", "历史", "通用"]）
    genres: List[str] = field(default_factory=lambda: ["通用"])
    # 步骤列表（按 order 排序）
    steps: List[TemplateStep] = field(default_factory=list)
    # 模板集级别的默认参数
    default_params: Dict[str, str] = field(default_factory=dict)

    def get_steps_in_order(self) -> List[TemplateStep]:
        """按 order 排序的步骤列表"""
        return sorted(self.steps, key=lambda s: s.order)

    def get_step(self, order: float) -> Optional[TemplateStep]:
        """获取指定序号的步骤"""
        for s in self.steps:
            if s.order == order:
                return s
        return None


class TemplateRegistry:
    """
    模板注册中心

    用法：
        registry = TemplateRegistry()
        registry.register(snowflake_template_set)
        template_set = registry.get("snowflake")
    """

    def __init__(self):
        self._templates: Dict[str, PromptTemplateSet] = {}

    def register(self, template_set: PromptTemplateSet) -> None:
        """注册模板集"""
        if template_set.name in self._templates:
            log.warning(f"模板集 '{template_set.name}' 已存在，将被覆盖")
        self._templates[template_set.name] = template_set
        log.info(f"已注册模板集: {template_set.display_name} ({template_set.name}) v{template_set.version}")

    def get(self, name: str) -> Optional[PromptTemplateSet]:
        """获取模板集"""
        return self._templates.get(name)

    def list(self) -> List[str]:
        """列出所有已注册的模板集名称"""
        return list(self._templates.keys())

    def list_with_info(self) -> List[dict]:
        """列出所有模板集及信息"""
        return [
            {
                "name": t.name,
                "display_name": t.display_name,
                "version": t.version,
                "description": t.description,
                "genres": t.genres,
                "steps": len(t.steps),
            }
            for t in self._templates.values()
        ]

    def load_builtin(self) -> None:
        """加载内置模板集"""
        from src.prompts.snowflake import SNOWFLAKE_TEMPLATE_SET
        from src.prompts.unified import UNIFIED_TEMPLATE_SET
        self.register(SNOWFLAKE_TEMPLATE_SET)
        self.register(UNIFIED_TEMPLATE_SET)


# 全局单例
_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """获取全局模板注册中心"""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
        _registry.load_builtin()
    return _registry
