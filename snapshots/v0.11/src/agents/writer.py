"""
WriterAgent — 章节写手

职责：
1. 接收章节上下文 + 章节号 + 用户指导
2. 内嵌章前规划（简化版 chapter_memo）
3. 生成章节正文
4. 返回结果 + 元数据
"""

import logging
from typing import Optional

from src.core.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResult
from src.utils.context_builder import ContextBuilder, ChapterContext
from src.utils.file_io import write_file, ensure_dir

log = logging.getLogger(__name__)

# Writer 系统提示词（写作规则）
WRITER_SYSTEM_PROMPT = """你是这本书的专职写手。你的任务是续写指定章节。

## 核心规则

1. 以简体中文写作，句子长短交替，段落适合手机阅读（3-5行/段）
2. 严格执行目标字数：不要大幅度超限也不要严重不足
3. 伏笔前后呼应，本章出现的新伏笔必须在后续章节回收
4. 人物行为由「过往经历 + 当前利益 + 性格底色」共同驱动，禁止突然降智或突然圣母
5. 场景描写必须有具体的五感细节——看到什么、听到什么、闻到什么、碰到什么
6. 章末必须留钩子——一个让读者想翻下一章的悬念或问题
7. 对话占比约30-50%，叙述占50-70%
8. 禁止使用「突然」「竟然」「原来」等偷懒转折词超过2次
9. 禁止机械降神——所有转折必须有前文铺垫
10. 避免AI味：不用「在这篇文章中」「综上所述」「值得注意的是」「不仅…更…」

## 风格遵循

如果上下文包含「风格指南」部分，你必须严格遵循其中描述的所有风格特征——叙事语气、对话风格、场景描写、节奏、词汇、情绪表达方式。
风格指南中的「去AI味对照表」和「六步推导法」内化为写作习惯，不机械套用。

## 输出格式

只输出章节正文，不要任何前言、后记、章节标题或注释。
正文用中文引号「」代替英文引号。对话用分段独立成段。"""


class WriterAgent(BaseAgent):
    """章节写手 Agent"""

    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)
        self._context_builder: Optional[ContextBuilder] = None

    @property
    def agent_name(self) -> str:
        return "Writer"

    async def run(self, context: AgentContext) -> AgentResult:
        """生成指定章节"""
        project_dir = context.project_dir
        ensure_dir(project_dir)

        extra = context.extra or {}
        chapter_number = extra.get("chapter_number", 1)
        user_guidance = context.user_guidance or ""
        word_count = extra.get("word_count", 3000)

        # 1. 加载上下文
        if self._context_builder is None:
            self._context_builder = ContextBuilder(project_dir)

        chapter_ctx = self._context_builder.build(chapter_number, user_guidance)

        # 2. 构建写作 prompt
        writing_prompt = self._build_writing_prompt(chapter_ctx, chapter_number, word_count)

        # 3. 调用 LLM 生成正文
        llm = self.get_llm_client()
        log.info(f"[Writer] 生成第 {chapter_number} 章 (prompt={len(writing_prompt)} 字)")

        response = await llm.chat_with_retry(
            prompt=writing_prompt,
            system_prompt=WRITER_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        chapter_text = response.content.strip()

        # 4. 基本校验
        if not chapter_text or len(chapter_text) < 100:
            return AgentResult(success=False, error="生成的章节过短")

        log.info(f"[Writer] 第 {chapter_number} 章完成 ({len(chapter_text)} 字)")

        # 将章节文本写回 context，便于 orchestrator 传递
        context.extra["chapter_text"] = chapter_text
        context.extra["chapter_number"] = chapter_number

        return AgentResult(
            success=True,
            context_updates={
                "chapter_text": chapter_text,
                "chapter_number": chapter_number,
            },
        )

    def _build_writing_prompt(self, ctx: ChapterContext, chapter_number: int,
                              word_count: int) -> str:
        """构建写作提示词"""
        context_text = ctx.build_prompt_context()
        guidance_text = ""
        if ctx.user_guidance:
            guidance_text = f"""
## 本章写作指导
{ctx.user_guidance}
"""

        return f"""请续写第 {chapter_number} 章。

{context_text}
{guidance_text}
## 写作要求

在动笔之前，请先在脑中完成以下规划（不要输出规划文字，只输出正文）：

### 本章规划（内化，不输出）
1. **本章核心事件**：一个 30 字以内的一句话概括
2. **角色出场**：本章会出现哪些角色、他们各自在做什么
3. **钩子管理**：哪些伏笔要推进/兑现？章末留什么新悬念？
4. **情绪曲线**：本章的情绪走向（开篇→中段→结尾）

### 正式写作
- 目标字数：{word_count} 字（允许 ±15%）
- 写一个完整的章节叙事——有开头、有冲突/进展、有结尾钩子
- 对话要推动情节或揭示人物，不是为了说话而说话
- 章末 200 字内必须有情绪落点——一个物象、一个动作、或一句耐人寻味的话

### 开始
请直接开始正文，不要写「第N章」「章节标题」等——这些我会后期加上。"""
