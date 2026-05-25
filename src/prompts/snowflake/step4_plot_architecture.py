"""
雪花写作法 — Step 4: 情节架构

按三幕式悬念结构设计完整情节。
"""
from src.prompts.base_template import TemplateStep

PLOT_ARCHITECTURE_STEP = TemplateStep(
    order=4,
    name="情节架构",
    description="三幕式悬念结构：触发→对抗→解决，每阶段含3个关键转折点",
    required_params=["user_guidance", "core_seed", "character_dynamics", "world_building", "character_names"],
    output_key="plot_architecture",
    prompt="""基于以下元素，设计完整的情节架构：

核心种子：{core_seed}
角色体系：{character_dynamics}
世界观：{world_building}
核心角色（请严格使用这些名称）：{character_names}
额外指导：{user_guidance}

按三幕式悬念结构设计：

## 第一幕：触发（约占 25%）
- 日常状态中的异常征兆（3处铺垫）
- 主线、暗线、副线的开端
- 打破平衡的催化剂事件
- 主角的认知局限导致的错误抉择

## 第二幕：对抗（约占 50%）
- 外部障碍升级 + 内部信念动摇
- 虚假胜利（看似解决，实则深化危机）
- 灵魂黑夜（世界观认知颠覆时刻）
- 主线与副线的交叉引爆点

## 第三幕：解决（约占 25%）
- 解决危机必须牺牲的核心价值
- 至少三层认知颠覆（表面解 → 新危机 → 终极抉择）
- 留下 2-3 个开放式悬念因子

每个阶段需包含 3 个关键转折点。使用精炼中文描述。
仅输出情节架构文本，不要任何解释。""",
)
