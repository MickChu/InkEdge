"""
雪花写作法 (Snowflake Method) — 提示词模板集

6 个步骤，按顺序执行：
  1. 核心种子 — 一句话概括故事本质
  2. 角色动力学 — 设计核心角色及弧线
  2.5. 初始角色状态 — 树形角色状态表
  3. 三维世界观 — 物理/社会/隐喻三维构建
  4. 情节架构 — 三幕式悬念结构
  5. 章节目录 — 悬念节奏曲线分布

适用于：奇幻、科幻、历史、都市、悬疑等所有类型。
"""

from src.prompts.base_template import PromptTemplateSet
from src.prompts.snowflake.step1_core_seed import CORE_SEED_STEP
from src.prompts.snowflake.step2_character_dynamics import CHARACTER_DYNAMICS_STEP
from src.prompts.snowflake.step25_character_state import CHARACTER_STATE_STEP
from src.prompts.snowflake.step3_world_building import WORLD_BUILDING_STEP
from src.prompts.snowflake.step4_plot_architecture import PLOT_ARCHITECTURE_STEP
from src.prompts.snowflake.step5_chapter_blueprint import CHAPTER_BLUEPRINT_STEP

SNOWFLAKE_TEMPLATE_SET = PromptTemplateSet(
    name="snowflake",
    display_name="雪花写作法",
    version="1.0",
    description=(
        "基于 Randy Ingermanson 的 Snowflake Method，从一句话核心逐步扩展到完整小说设定。"
        "融合角色弧光理论、三维世界观构建、三幕式悬念结构，适合长篇小说的系统性规划。"
    ),
    genres=["通用", "奇幻", "科幻", "历史", "都市", "悬疑", "武侠"],
    steps=[
        CORE_SEED_STEP,
        CHARACTER_DYNAMICS_STEP,
        CHARACTER_STATE_STEP,
        WORLD_BUILDING_STEP,
        PLOT_ARCHITECTURE_STEP,
        CHAPTER_BLUEPRINT_STEP,
    ],
)
