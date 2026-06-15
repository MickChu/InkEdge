"""
雪花写作法 — Step 5: 章节目录
按悬念节奏曲线设计章节分布，每章含元数据标注。
"""
from src.prompts.base_template import TemplateStep

CHAPTER_BLUEPRINT_STEP = TemplateStep(
    order=5,
    name="章节目录",
    description="设计章节的节奏分布，每章标注悬念密度、伏笔操作、转折等级",
    required_params=["user_guidance", "novel_architecture", "number_of_chapters", "character_names"],
    output_key="chapter_blueprint",
    output_file="Novel_directory.txt",
    prompt="""基于以下小说架构，设计 {number_of_chapters} 章的详细章节目录：

{novel_architecture}

额外指导：{user_guidance}

设计原则：
1. 每 3-5 章构成一个悬念单元，包含完整的小高潮
2. 单元之间设置"认知过山车"（紧张→缓冲→再紧张）
3. 关键转折章预留多视角铺垫
4. 在前 {number_of_chapters} 章内不出现结局

每章需明确标注：
- 章节定位（角色引入/冲突升级/信息揭示/情感爆发/转折/缓冲）
- 核心作用（推进主线/展开伏笔/回收伏笔/世界观扩展）
- 悬念密度（紧凑★★★/渐进★★/缓冲★）
- 伏笔操作（埋设XX/强化XX/回收XX/无）
- 认知颠覆强度（1-5级，5为最大颠覆）
- 一句话简述（20字以内）

输出格式：
第1章 - 【标题】
本章定位：【角色/事件/主题】
核心作用：【推进/转折/揭示】
悬念密度：【★★★/★★/★】
伏笔操作：【埋设XX线索→强化YY矛盾】
认知颠覆：【★★☆☆☆】
本章简述：【一句话概括】

...

仅输出章节目录文本，不要任何解释。""",
)
