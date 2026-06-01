"""
StyleAnalyzer — 从作家作品片段自动提取结构化风格指南

输入：用户收集的作家原文片段（可能来自多个相近风格作家）
输出：8 维风格指南 → style_guide.md

8 个分析维度：
1. 叙事声音与语气
2. 对话风格
3. 场景描写特征
4. 转折与衔接手法
5. 节奏特征
6. 词汇偏好
7. 情绪表达方式
8. 独特习惯

每个维度包含：
- 散文式总结（2-4句）
- 引用原片段中的具体例子（至少2个）
"""

import logging
import os
from typing import Optional

from src.core.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResult
from src.utils.file_io import read_file, write_file

log = logging.getLogger(__name__)

STYLE_ANALYZER_SYSTEM = """你是一位文学风格分析师。你的任务是从给定的作家作品片段中，提取结构化的风格指南。

## 分析规则

1. 识别共性：找出所有片段的共同风格特征（不是每个作家分别分析，是提炼他们共有的笔法）
2. 具体引用：每个观察必须附带原文片段作为证据（用 > 引用块）
3. 可行指导：输出的是给写手的指令，不是文学评论——要说"怎么做到"，不能说"这里很棒"
4. 严格聚焦 8 个维度，每个维度写 3-5 句总结 + 至少 2 个例子

## 8 个维度

### 1. 叙事声音与语气
叙述者的态度、与读者的距离、是否夹杂评价或讽刺。

### 2. 对话风格
句子长短、文白程度、角色辨识度、潜台词处理。

### 3. 场景描写特征
感官偏好（视觉/听觉/嗅觉/触觉）、空间交代方式、环境与情绪的关系。

### 4. 转折与衔接手法
段落间过渡方式、视角切换技巧、时间跳跃处理。

### 5. 节奏特征
长句与短句的比例、段落长度的功能分配、打斗/对话/叙述的节奏差异。

### 6. 词汇偏好
高频词类、文白比例、比喻意象偏好、专业术语使用。

### 7. 情绪表达方式
外化手法（动作/表情/对话替代直白心理）、内心活动的呈现方式。

### 8. 独特习惯
该风格特有的标志性手法、反复出现的叙事装置。

## 输出格式

```
## 叙事声音与语气
（3-5句总结）
- "原文片段1"
- "原文片段2"

## 对话风格
...

## 写作方法参考（以下规则必须在写作中内化）

### 一、去AI味正反例对照（从本风格角度重写）

| 反例 | 正例 | 要点 |
| ...（至少5行）

### 二、人物心理推导六步（可选，如果片段展示了大量心理描写）
```
"""

STYLE_ANALYZER_PROMPT = """请分析以下作家作品片段，提取共有的风格特征。

## 风格分析素材

{content}

---

请按以下格式输出分析结果。每个维度必须包含总结段落和至少两个原文例子。

## 叙事声音与语气
## 对话风格
## 场景描写特征
## 转折与衔接手法
## 节奏特征
## 词汇偏好
## 情绪表达方式
## 独特习惯
## 写作方法参考

写作方法参考部分必须包含：
1. 去AI味对照表（从该风格角度，写出5组反例→正例）
2. 如果片段中展示了复杂人物心理，补充六步推导法
"""


class StyleAnalyzer(BaseAgent):
    """自动分析作家片段 → 输出结构化 style_guide.md"""

    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)

    @property
    def agent_name(self) -> str:
        return "StyleAnalyzer"

    async def run(self, context: AgentContext) -> AgentResult:
        extra = context.extra or {}
        fragments_path = extra.get("fragments_path", "")
        output_path = extra.get("output_path", "")

        # 读取片段
        if fragments_path and os.path.isfile(fragments_path):
            fragments = read_file(fragments_path, default="")
        elif context.user_guidance:
            fragments = context.user_guidance
        else:
            return AgentResult(success=False, error="没有提供风格分析素材")

        if len(fragments) < 200:
            return AgentResult(success=False, error="素材太短（<200字），无法提取风格特征")

        log.info(f"[StyleAnalyzer] 分析 {len(fragments)} 字风格素材")
        llm = self.get_llm_client()

        response = await llm.chat_with_retry(
            prompt=STYLE_ANALYZER_PROMPT.format(content=fragments),
            system_prompt=STYLE_ANALYZER_SYSTEM,
            max_tokens=4096,
        )

        style_guide = response.content.strip()
        if not style_guide or len(style_guide) < 300:
            return AgentResult(success=False, error="风格分析输出过短")

        # 保存
        if not output_path:
            output_path = os.path.join(context.project_dir, "style_guide.md")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        write_file(output_path, style_guide)
        log.info(f"[StyleAnalyzer] 风格指南已保存: {output_path} ({len(style_guide)} 字)")

        return AgentResult(
            success=True,
            context_updates={
                "style_guide_path": output_path,
                "style_guide_length": len(style_guide),
            },
        )


# 便捷函数
async def analyze_style_fragments(
    project_dir: str,
    fragments_path: str = "",
    fragments_text: str = "",
    output_path: str = "",
) -> AgentResult:
    """分析风格片段并保存"""
    agent = StyleAnalyzer()
    context = AgentContext(
        project_dir=project_dir,
        user_guidance=fragments_text,
    )
    if fragments_path:
        context.extra = {"fragments_path": fragments_path, "output_path": output_path}
    elif output_path:
        context.extra = {"output_path": output_path}
    return await agent.safe_run(context)
