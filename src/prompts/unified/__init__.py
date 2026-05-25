"""
统一基础设定 (Unified Foundation) — inkOS 风格提示词模板

相比于雪花写作法（6 步分步生成），统一模板一次 LLM 调用输出全部 5 段：
  story_frame / volume_map / roles / book_rules / pending_hooks

世界观不是独立文档，而是 story_frame 的第 3 段——与核心冲突、主题基调
天然融合，一个故事一个世界观。
"""

from src.prompts.base_template import PromptTemplateSet
from src.prompts.unified.step_foundation import UNIFIED_FOUNDATION_STEP

UNIFIED_TEMPLATE_SET = PromptTemplateSet(
    name="unified",
    display_name="统一基础设定",
    version="1.0",
    description=(
        "一次 LLM 调用生成完整小说基础设定。世界观融入故事框架，"
        "不做独立百科全书。模仿 inkOS 的 Architect Agent 设计哲学："
        "散文密度、严格去重、预算约束、前台/后台双层故事。"
    ),
    genres=["通用", "奇幻", "科幻", "历史", "都市", "悬疑", "武侠"],
    steps=[UNIFIED_FOUNDATION_STEP],
)
