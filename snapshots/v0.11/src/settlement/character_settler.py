"""
Phase 11 — CharacterSettler: 角色状态结算

更新情感弧线（emotional_arcs.md）和角色交互矩阵（character_matrix.md）。
"""
import re
import logging
from dataclasses import dataclass

from src.utils.file_io import read_file, write_file

log = logging.getLogger(__name__)


@dataclass
class CharacterSettleOutput:
    post_settlement: str = ""
    updated_emotional_arcs: str = ""
    updated_character_matrix: str = ""


def parse_character_output(content: str) -> CharacterSettleOutput:
    out = CharacterSettleOutput()
    for tag in ("POST_SETTLEMENT", "UPDATED_EMOTIONAL_ARCS", "UPDATED_CHARACTER_MATRIX"):
        pattern = rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)"
        m = re.search(pattern, content)
        if m:
            key = "updated_emotional_arcs" if "EMOTIONAL" in tag else \
                  "updated_character_matrix" if "MATRIX" in tag else \
                  "post_settlement"
            setattr(out, key, m.group(1).strip())
    return out


class CharacterSettler:
    """角色状态结算器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.state_dir = f"{project_dir}/story/state"

    async def settle(self, chapter_number: int, observations: str,
                     llm_client, volume_outline: str = "") -> CharacterSettleOutput:
        from .prompt_templates import CHARACTER_SETTLER_SYSTEM, CHARACTER_SETTLER_USER

        emotional_arcs = self._read("emotional_arcs.md", "（文件尚未创建）")
        character_matrix = self._read("character_matrix.md", "（文件尚未创建）")

        user = CHARACTER_SETTLER_USER.format(
            chapter_number=chapter_number,
            observations=observations,
            emotional_arcs=emotional_arcs,
            character_matrix=character_matrix,
            volume_outline=volume_outline or "（无卷纲）",
        )

        try:
            response = await llm_client.chat(
                prompt=user,
                system_prompt=CHARACTER_SETTLER_SYSTEM,
                temperature=0.3,
                max_tokens=2500,
            )
            output = parse_character_output(response.content)
            self._save(output, chapter_number)
            return output
        except Exception as e:
            log.warning(f"[CharacterSettler] 结算失败: {e}")
            return CharacterSettleOutput(post_settlement=f"结算失败: {e}")

    def _read(self, filename: str, default: str) -> str:
        path = f"{self.state_dir}/{filename}"
        import os
        if os.path.exists(path):
            return read_file(path, default=default)
        return default

    def _save(self, output: CharacterSettleOutput, chapter_number: int):
        import os
        os.makedirs(self.state_dir, exist_ok=True)

        if output.updated_emotional_arcs:
            write_file(f"{self.state_dir}/emotional_arcs.md",
                       output.updated_emotional_arcs)

        if output.updated_character_matrix:
            write_file(f"{self.state_dir}/character_matrix.md",
                       output.updated_character_matrix)

        log.info(f"[CharacterSettler] 第{chapter_number}章角色状态已结算")
