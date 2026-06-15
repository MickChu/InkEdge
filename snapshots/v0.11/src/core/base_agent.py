"""
BaseAgent — 所有 Agent 的抽象基类

设计理念（来自 inkOS）：
- 每个 Agent 是一个独立的"智能体"，有明确的职责边界
- Agent 之间通过 Orchestrator 编排，不直接通信
- 每个 Agent 有独立的 LLM 客户端配置（可不同模型/温度）
- 支持生命周期钩子：setup → run → teardown
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import logging

log = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 运行配置"""
    model_name: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 600
    # 允许覆写 API 配置，默认从全局配置继承
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    interface_format: str = "OpenAI"


@dataclass
class AgentContext:
    """Agent 执行上下文——在 Agent 间流转的共享状态"""
    # 项目路径
    project_dir: str = ""
    # 已生成的小说设定文本
    foundation: str = ""
    # 全局摘要
    global_summary: str = ""
    # 角色状态文本
    character_state: str = ""
    # 章节目录文本
    chapter_blueprint: str = ""
    # 用户指导
    user_guidance: str = ""
    # 额外数据（各 Agent 可自定义写入）
    extra: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    # 更新后的上下文（如有变更）
    context_updates: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Agent 基类——所有小说生成 Agent 的父类"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self._llm_client = None

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent 唯一标识名"""
        ...

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Agent 主执行逻辑"""
        ...

    async def setup(self, context: AgentContext) -> None:
        """执行前准备（可选覆写）"""
        log.info(f"[{self.agent_name}] setup")

    async def teardown(self, context: AgentContext) -> None:
        """执行后清理（可选覆写）"""
        log.info(f"[{self.agent_name}] teardown")

    def get_llm_client(self):
        """懒加载 LLM 客户端"""
        if self._llm_client is None:
            from src.utils.llm_client import LLMClient
            self._llm_client = LLMClient(
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                interface_format=self.config.interface_format,
            )
        return self._llm_client

    async def safe_run(self, context: AgentContext) -> AgentResult:
        """带生命周期管理的安全执行"""
        try:
            await self.setup(context)
            result = await self.run(context)
            await self.teardown(context)
            return result
        except Exception as e:
            log.error(f"[{self.agent_name}] 执行异常: {e}", exc_info=True)
            return AgentResult(success=False, error=str(e))
