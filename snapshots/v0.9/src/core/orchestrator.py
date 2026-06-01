"""
Orchestrator — Agent 编排引擎

设计理念（来自 inkOS pipeline）：
- 按预定 DAG（有向无环图）编排 Agent 执行顺序
- 支持串行/并行执行
- 上下文在 Agent 间自动传递和更新
- 支持断点续传（阶段性数据持久化）
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

from .base_agent import BaseAgent, AgentContext, AgentResult

log = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """流水线步骤"""
    agent: BaseAgent
    # 是否必须成功才能继续
    required: bool = True
    # 最大重试次数
    max_retries: int = 2
    # 是否可断点续传（跳过已完成的步骤）
    resumable: bool = True


@dataclass
class PipelineResult:
    """流水线执行结果"""
    success: bool
    steps_completed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    final_context: Optional[AgentContext] = None
    error: str = ""


class Orchestrator:
    """Agent 编排器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.checkpoint_file = os.path.join(project_dir, ".inkedge_checkpoint.json")

    def _load_checkpoint(self) -> dict:
        """加载断点数据"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_checkpoint(self, data: dict) -> None:
        """保存断点数据"""
        os.makedirs(self.project_dir, exist_ok=True)
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def run_sequential(
        self,
        steps: List[PipelineStep],
        context: AgentContext,
        on_step_complete: Optional[Callable] = None,
    ) -> PipelineResult:
        """
        串行执行流水线：
        Step1 → Step2 → Step3 → ...
        前一步输出作为后一步的上下文输入
        """
        result = PipelineResult(success=True, final_context=context)
        checkpoint = self._load_checkpoint()

        for i, step in enumerate(steps):
            agent_name = step.agent.agent_name

            # 断点续传：跳过已完成步骤
            if step.resumable and checkpoint.get(agent_name) == "done":
                log.info(f"[{agent_name}] 已标记完成，跳过")
                result.steps_completed.append(agent_name)
                continue

            log.info(f"[Orchestrator] 执行 Step {i+1}: {agent_name}")

            # 带重试的执行
            agent_result = None
            for attempt in range(step.max_retries + 1):
                if attempt > 0:
                    log.warning(f"[{agent_name}] 重试 {attempt}/{step.max_retries}")
                agent_result = await step.agent.safe_run(context)
                if agent_result.success:
                    break

            if agent_result is None or not agent_result.success:
                error_msg = agent_result.error if agent_result else "未知错误"
                log.error(f"[{agent_name}] 执行失败: {error_msg}")
                result.steps_failed.append(agent_name)
                if step.required:
                    result.success = False
                    result.error = f"Step {agent_name} 失败: {error_msg}"
                    return result
                continue

            # 应用上下文更新
            if agent_result.context_updates:
                for key, value in agent_result.context_updates.items():
                    if hasattr(context, key):
                        setattr(context, key, value)

            result.steps_completed.append(agent_name)

            # 保存断点
            if step.resumable:
                checkpoint[agent_name] = "done"
                self._save_checkpoint(checkpoint)

            # 步骤完成的回调
            if on_step_complete:
                on_step_complete(agent_name, agent_result)

        return result

    async def run_parallel(
        self,
        agents: List[BaseAgent],
        context: AgentContext,
    ) -> Dict[str, AgentResult]:
        """
        并行执行多个 Agent：
        适用于无依赖关系的任务（如同步更新世界/角色/情节状态）
        """
        tasks = [agent.safe_run(context) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: Dict[str, AgentResult] = {}
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                output[agent.agent_name] = AgentResult(
                    success=False, error=str(result)
                )
            else:
                output[agent.agent_name] = result

        return output

    def clear_checkpoint(self) -> None:
        """清除断点——重新开始整个流水线"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
