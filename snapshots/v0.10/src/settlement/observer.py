"""
Phase 11 — Observer: 事实提取Agent

每章写完后，Observer 从正文中提取所有可观察事实。
输出结构化观察日志，供三个 Settler 并行结算。
"""
import logging
from typing import Optional

from .prompt_templates import OBSERVER_SYSTEM, OBSERVER_USER

log = logging.getLogger(__name__)


class Observer:
    """事实提取器"""

    def __init__(self):
        pass

    async def observe(self, chapter_text: str, chapter_number: int,
                      llm_client) -> str:
        """
        从章节正文提取所有事实变化。

        Args:
            chapter_text: 章节全文
            chapter_number: 章号
            llm_client: LLM 客户端

        Returns:
            observations: 结构化观察日志
        """
        system = OBSERVER_SYSTEM
        user = OBSERVER_USER.format(
            chapter_number=chapter_number,
            chapter_text=chapter_text[:8000],  # 长章截断
        )

        try:
            response = await llm_client.chat(
                prompt=user,
                system_prompt=system,
                temperature=0.2,
                max_tokens=3000,
            )
            return response.content
        except Exception as e:
            log.warning(f"[Observer] LLM 提取失败: {e}")
            return f"=== OBSERVATIONS ===\n(提取失败: {e})"

    def observe_sync(self, chapter_text: str, chapter_number: int) -> str:
        """
        同步版：基于正则的基础提取（无需 LLM）。

        精度远低于 LLM 版，但可在离线/降级场景使用。
        """
        import re

        lines = ["=== OBSERVATIONS ===", ""]

        # [角色行为] — 提取人名+动词模式
        lines.append("[角色行为]")
        name_actions = set()
        for m in re.finditer(r'([沈赵李王张刘陈杨吴周][\u4e00-\u9fff]{1,2})(?:[^，。！？]{1,20})([来到走跑看想想问说答叫喊笑哭打杀闯进出入取拿放用挥举踢])', chapter_text):
            name_actions.add(f"- {m.group(1)}: {m.group(2)}")
        for line in list(name_actions)[:10]:
            lines.append(line)
        lines.append("")

        # [位置变化]
        lines.append("[位置变化]")
        places_found = set()
        for m in re.finditer(r'(?:到了?|来到|走进|进入|离开|走出|前往|回到)([\u4e00-\u9fff]{2,6}(?:殿|厅|房|室|阁|楼|城|镇|村|山|谷|街|巷|庙|院|铺))', chapter_text):
            places_found.add(f"- 角色移动到: {m.group(1)}")
        for line in list(places_found)[:8]:
            lines.append(line)
        lines.append("")

        # [资源变化]
        lines.append("[资源变化]")
        for m in re.finditer(r'(?:得到|获得|捡起|取出|拿出|给了?|交给|送给|扔|丢弃|掉|花|花费|买了?|用掉了?)(?:了\s*)?(.{2,15}?(?:剑|刀|丹|药|石|令|牌|袋|瓶|匣|卷|书|镜|珠|绳|针|甲|符|印|扇|锤|环|钩|索|钱|银|金|币|两|文|串))', chapter_text):
            lines.append(f"- 资源变化: {m.group(0).strip()[:30]}")
        lines.append("")

        # [情绪变化]
        lines.append("[情绪变化]")
        for m in re.finditer(r'(\S{2,3})(?:感到|觉得|变得|忽然|突然|一下)?(愤怒|恐惧|害怕|紧张|安心|放心|高兴|兴奋|悲伤|难过|感动|困惑|惊讶|震惊|后悔)(?:了|起来)?', chapter_text):
            lines.append(f"- {m.group(1)}: → {m.group(2)}")
        lines.append("")

        # [剧情线索]
        lines.append("[剧情线索]")
        for m in re.finditer(r'(?:发现|得知|听说|收到消息|信件|密信|暗号|印记|秘密|机关|暗门|地道|真相)(.{0,20}?)', chapter_text):
            clue = m.group(0).strip()[:40]
            if len(clue) >= 4:
                lines.append(f"- 线索: {clue}")
                if len(lines) >= 12:
                    break
        lines.append("")

        return "\n".join(lines)
