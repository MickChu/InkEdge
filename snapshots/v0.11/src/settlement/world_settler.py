"""
Phase 11 — WorldSettler: 世界观状态结算

更新状态卡（current_state.md）和资源账本（ledger.md）。
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass

from src.utils.file_io import read_file, write_file

log = logging.getLogger(__name__)


@dataclass
class WorldSettleOutput:
    post_settlement: str = ""
    updated_state: str = ""
    updated_ledger: str = ""


def parse_world_output(content: str) -> WorldSettleOutput:
    """解析 WorldSettler 的 === TAG === 输出"""
    out = WorldSettleOutput()

    for tag in ("POST_SETTLEMENT", "UPDATED_STATE", "UPDATED_LEDGER"):
        pattern = rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)"
        m = re.search(pattern, content)
        if m:
            setattr(out, tag.lower(), m.group(1).strip())

    return out


class WorldSettler:
    """世界观状态结算器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.state_dir = f"{project_dir}/story/state"

    async def settle(self, chapter_number: int, observations: str,
                     llm_client) -> WorldSettleOutput:
        """
        异步结算（LLM 版）。

        Args:
            chapter_number: 章号
            observations: Observer 提取的观察日志
            llm_client: LLM 客户端

        Returns:
            WorldSettleOutput
        """
        from .prompt_templates import WORLD_SETTLER_SYSTEM, WORLD_SETTLER_USER

        current_state = self._read_file("current_state.md", "（尚无状态卡）")
        current_ledger = self._read_file("ledger.md", "（尚无账本）")

        user = WORLD_SETTLER_USER.format(
            chapter_number=chapter_number,
            observations=observations,
            current_state=current_state,
            current_ledger=current_ledger,
        )

        try:
            response = await llm_client.chat(
                prompt=user,
                system_prompt=WORLD_SETTLER_SYSTEM,
                temperature=0.2,
                max_tokens=2000,
            )
            output = parse_world_output(response.content)
            self._save(output, chapter_number)
            return output
        except Exception as e:
            log.warning(f"[WorldSettler] 结算失败: {e}")
            return WorldSettleOutput(post_settlement=f"结算失败: {e}")

    def _read_file(self, filename: str, default: str = "") -> str:
        path = f"{self.state_dir}/{filename}"
        import os
        return read_file(path, default=default) if os.path.exists(path) else default

    def _save(self, output: WorldSettleOutput, chapter_number: int):
        import os
        os.makedirs(self.state_dir, exist_ok=True)

        if output.updated_state:
            write_file(f"{self.state_dir}/current_state.md", output.updated_state)

        if output.updated_ledger:
            write_file(f"{self.state_dir}/ledger.md", output.updated_ledger)

        log.info(f"[WorldSettler] 第{chapter_number}章世界观状态已结算")
