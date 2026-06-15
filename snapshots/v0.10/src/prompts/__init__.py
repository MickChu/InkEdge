"""
prompts — 提示词模板系统

架构：
  base_template.py     — TemplateStep / PromptTemplateSet / TemplateRegistry
  snowflake/           — 雪花写作法模板集（6步）
    step1_core_seed.py
    step2_character_dynamics.py
    step25_character_state.py
    step3_world_building.py
    step4_plot_architecture.py
    step5_chapter_blueprint.py

添加新模板集的步骤：
  1. 在 prompts/ 下新建目录（如 heros_journey/）
  2. 每个步骤一个 .py 文件，export 一个 TemplateStep
  3. 在目录的 __init__.py 中组装 PromptTemplateSet
  4. 在 base_template.py 的 load_builtin() 中注册

使用方式：
  from src.prompts import get_template_registry
  registry = get_template_registry()
  template_set = registry.get("snowflake")
"""

from .base_template import (
    TemplateStep,
    PromptTemplateSet,
    TemplateRegistry,
    get_template_registry,
)

__all__ = [
    "TemplateStep",
    "PromptTemplateSet", 
    "TemplateRegistry",
    "get_template_registry",
]
