"""
雪花写作法 — Step 1: 核心种子

一句话概括故事本质，包含主角身份、核心事件、关键行动、灾难后果、隐藏危机。
"""
from src.prompts.base_template import TemplateStep

CORE_SEED_STEP = TemplateStep(
    order=1,
    name="核心种子",
    description="用一句话（50-200字）概括故事本质，包含显性冲突与潜在危机",
    required_params=["topic", "genre", "number_of_chapters", "word_number"],
    output_key="core_seed",
    prompt="""你是一位经验丰富的小说架构师。请用"雪花写作法"第一步，为以下故事构建核心种子：

主题：{topic}
类型：{genre}
规划篇幅：约 {number_of_chapters} 章（每章约 {word_number} 字）

请用一句话（50-200字）概括故事的本质。要求包含：
1. 主角的核心身份与驱动力
2. 打破平衡的关键事件
3. 必须完成的关键行动
4. 失败的灾难性后果
5. 隐藏的更大危机

输出格式示例：
"当[主角身份]遭遇[核心事件]，必须[关键行动]，否则[灾难后果]；与此同时，[隐藏的更大危机]正在暗处发酵。"

仅输出核心种子文本，不要任何解释。""",
)
