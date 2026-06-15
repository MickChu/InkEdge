"""
雪花写作法 — Step 2.5: 初始角色状态

基于角色动力学生成树形角色状态表（物品/能力/关系/经历）。
"""
from src.prompts.base_template import TemplateStep

CHARACTER_STATE_STEP = TemplateStep(
    order=2.5,
    name="初始角色状态",
    description="为每个角色生成树形状态表（物品/能力/关系/关键经历）",
    required_params=["character_dynamics"],
    output_key="character_state",
    output_file="character_state.txt",
    prompt="""基于以下角色动力学设定，生成初始角色状态表：

{character_dynamics}

每个角色按以下树形格式描述：

【角色名】
├── 物品
│   ├── （物品名）：（描述其外观、来历、象征意义）
│   └── ...
├── 能力
│   ├── 技能1：（描述及当前掌握程度）
│   └── 技能2：...
├── 状态
│   ├── 身体状态：（当前身体状况）
│   └── 心理状态：（当前心理状态与内心矛盾）
├── 核心关系
│   ├── 与【角色A】：（关系性质与动态）
│   └── 与【角色B】：...
└── 关键经历
    ├── 事件1：（对角色产生深远影响的事件）
    └── 事件2：...

仅输出角色状态文本，不要任何解释。""",
)
