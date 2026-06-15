"""
Phase 11 — PlotSettler: 情节结构结算

更新伏笔池（hooks.md）、章节摘要（chapter_summaries.md）、支线面板（subplots.md）。
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.utils.file_io import read_file, write_file

log = logging.getLogger(__name__)


@dataclass
class PlotSettleOutput:
    post_settlement: str = ""
    updated_hooks: str = ""
    chapter_summary: str = ""
    updated_chapter_summaries: str = ""
    updated_subplots: str = ""


def parse_plot_output(content: str) -> PlotSettleOutput:
    out = PlotSettleOutput()
    tag_map = {
        "POST_SETTLEMENT": "post_settlement",
        "UPDATED_HOOKS": "updated_hooks",
        "CHAPTER_SUMMARY": "chapter_summary",
        "UPDATED_CHAPTER_SUMMARIES": "updated_chapter_summaries",
        "UPDATED_SUBPLOTS": "updated_subplots",
    }
    for tag, attr in tag_map.items():
        pattern = rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)"
        m = re.search(pattern, content)
        if m:
            setattr(out, attr, m.group(1).strip())
    return out


class PlotSettler:
    """情节结构结算器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.state_dir = f"{project_dir}/story/state"

    async def settle(self, chapter_number: int, observations: str,
                     llm_client, chapter_count: int = 0,
                     volume_outline: str = "") -> PlotSettleOutput:
        from .prompt_templates import PLOT_SETTLER_SYSTEM, PLOT_SETTLER_USER

        hooks = self._read("hooks.md", "（尚无伏笔）")
        summaries = self._read("chapter_summaries.md", "（文件尚未创建）")
        subplots = self._read("subplots.md", "（尚无支线）")

        user = PLOT_SETTLER_USER.format(
            chapter_number=chapter_number,
            observations=observations,
            current_hooks=hooks,
            chapter_summaries=summaries,
            current_subplots=subplots,
            volume_outline=volume_outline or "（无卷纲）",
        )

        # 注入章节数
        user = user.replace("{chapters_count}", str(chapter_count or "N"))

        try:
            response = await llm_client.chat(
                prompt=user,
                system_prompt=PLOT_SETTLER_SYSTEM,
                temperature=0.3,
                max_tokens=3000,
            )
            output = parse_plot_output(response.content)
            self._save(output, chapter_number)
            return output
        except Exception as e:
            log.warning(f"[PlotSettler] 结算失败: {e}")
            return PlotSettleOutput(post_settlement=f"结算失败: {e}")

    def _read(self, filename: str, default: str) -> str:
        path = f"{self.state_dir}/{filename}"
        import os
        if os.path.exists(path):
            return read_file(path, default=default)
        return default

    def _save(self, output: PlotSettleOutput, chapter_number: int):
        import os
        os.makedirs(self.state_dir, exist_ok=True)

        if output.updated_hooks:
            write_file(f"{self.state_dir}/hooks.md", output.updated_hooks)

        if output.updated_chapter_summaries:
            write_file(f"{self.project_dir}/chapter_summaries.md",
                       output.updated_chapter_summaries)

        if output.updated_subplots:
            write_file(f"{self.state_dir}/subplots.md", output.updated_subplots)

        log.info(f"[PlotSettler] 第{chapter_number}章情节结构已结算")
