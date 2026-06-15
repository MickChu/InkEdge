"""
雪花写作法 — Step 2: 角色动力学

基于角色弧光模型，设计3-6个有动态变化潜力的核心角色。
"""
from src.prompts.base_template import TemplateStep

CHARACTER_DYNAMICS_STEP = TemplateStep(
    order=2,
    name="角色动力学",
    description="设计3-6个核心角色，含驱动力三角、角色弧线、关系冲突网",
    required_params=["user_guidance", "core_seed"],
    output_key="character_dynamics",
    prompt="""基于以下元素，设计 3-6 个具有动态变化潜力的核心角色：

核心种子：{core_seed}
额外指导（如有）：{user_guidance}

每个角色需包含以下信息：

1. 基础档案
   - 姓名、年龄、性别、外貌特征
   - 身份/职业、社会地位
   - 隐藏的秘密或致命弱点

2. 核心驱动力三角
   - 表面追求（物质/可见的目标）
   - 深层渴望（情感/心理的需求）
   - 灵魂需求（哲学/存在的意义）

3. 角色弧线
   初始状态 → 触发事件 → 认知失调 → 蜕变节点 → 最终状态

4. 关系冲突网
   - 与至少两个其他角色的价值观冲突
   - 一个意外的合作或纽带
   - 一个潜在的背叛可能性

要求：
- 使用清晰的中文描述
- 角色之间应形成有机的互动网络
- 避免脸谱化，给予每个角色内在矛盾

仅输出角色设定文本，不要任何解释。""",
)
