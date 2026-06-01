"""
数据源实现: 番茄小说、起点中文网、离线知识回退
"""
from abc import ABC, abstractmethod
from typing import List
from .base import RadarSource, RadarEntry, RadarReport


class FanqieRadarSource(RadarSource):
    """番茄小说排行榜（网络爬取）"""
    name = "fanqie"

    async def fetch(self, genre: str = "", limit: int = 30) -> RadarReport:
        import re
        import aiohttp

        entries: List[RadarEntry] = []
        url = "https://fanqienovel.com/rank/all"
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return self.offline_fallback(genre, limit)
                    html = await resp.text()

            # 简易 HTML 提取: 书名在 data-title 或 title attr
            titles = re.findall(r'data-title="([^"]+)"', html)[:limit]
            for i, t in enumerate(titles, 1):
                entries.append(RadarEntry(rank=i, title=t, source="fanqie"))

            return RadarReport(source=self.name, entries=entries or [],
                               note="" if entries else "未提取到有效数据")

        except Exception:
            return self.offline_fallback(genre, limit)

    def offline_fallback(self, genre: str = "", limit: int = 30) -> RadarReport:
        entries = self._get_static_data(genre)[:limit]
        return RadarReport(source=self.name, entries=entries,
                           note="离线回退数据（非实时）")

    def _get_static_data(self, genre: str) -> List[RadarEntry]:
        return [
            RadarEntry(rank=1, title="诸神游戏", author="烽火戏诸侯",
                       genre="奇幻", popularity=9800, word_count="120万",
                       status="连载", tags=["奇幻", "史诗"], source="fanqie"),
            RadarEntry(rank=2, title="双月无辉", author="猫腻",
                       genre="玄幻", popularity=9500, word_count="200万",
                       status="连载", tags=["玄幻", "修炼"], source="fanqie"),
            RadarEntry(rank=3, title="蜀山问剑", author="管平潮",
                       genre="仙侠", popularity=9200, word_count="180万",
                       status="连载", tags=["仙侠", "剑修"], source="fanqie"),
        ]


class QidianRadarSource(RadarSource):
    """起点中文网排行榜（网络爬取）"""
    name = "qidian"

    async def fetch(self, genre: str = "", limit: int = 30) -> RadarReport:
        import re
        import aiohttp

        entries: List[RadarEntry] = []
        url = "https://www.qidian.com/rank/readIndex/"
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status != 200:
                        return self.offline_fallback(genre, limit)
                    html = await resp.text()

            titles = re.findall(r'data-title="([^"]+)"', html)[:limit]
            for i, t in enumerate(titles, 1):
                entries.append(RadarEntry(rank=i, title=t, source="qidian"))

            return RadarReport(source=self.name, entries=entries or [],
                               note="" if entries else "未提取到有效数据")

        except Exception:
            return self.offline_fallback(genre, limit)

    def offline_fallback(self, genre: str = "", limit: int = 30) -> RadarReport:
        entries = self._get_static_data(genre)[:limit]
        return RadarReport(source=self.name, entries=entries,
                           note="离线回退数据（非实时）")

    def _get_static_data(self, genre: str) -> List[RadarEntry]:
        return [
            RadarEntry(rank=1, title="夜的命名术", author="会说话的肘子",
                       genre="都市", popularity=10200, word_count="300万",
                       status="连载", tags=["都市", "异能"], source="qidian"),
            RadarEntry(rank=2, title="大奉打更人", author="卖报小郎君",
                       genre="仙侠", popularity=11000, word_count="380万",
                       status="连载", tags=["仙侠", "破案"], source="qidian"),
            RadarEntry(rank=3, title="诡秘之主", author="爱潜水的乌贼",
                       genre="奇幻", popularity=12500, word_count="447万",
                       status="完结", tags=["奇幻", "克苏鲁"], source="qidian"),
        ]


class KnowledgeRadarSource(RadarSource):
    """
    离线知识回退——当所有在线数据源都不可用时使用。

    基于对网文市场的静态知识，确保组件在任何网络条件下都能给出有意义的建议。
    """
    name = "knowledge"

    async def fetch(self, genre: str = "", limit: int = 30) -> RadarReport:
        return self.offline_fallback(genre, limit)

    def offline_fallback(self, genre: str = "", limit: int = 30) -> RadarReport:
        all_data = self._get_market_knowledge()
        entries = [e for e in all_data if not genre or genre in e.tags or genre in e.genre]
        return RadarReport(
            source=self.name,
            entries=entries[:limit] or all_data[:limit],
            note="基于知识的市场趋势（非实时数据）",
        )

    def _get_market_knowledge(self) -> List[RadarEntry]:
        return [
            RadarEntry(rank=1, title="大宋秘谍", author="—",
                       genre="历史架空", popularity=8500, word_count="—",
                       status="—", tags=["历史", "谍战", "穿越"],
                       summary="2024-2025 历史谍战类兴起", source="knowledge"),
            RadarEntry(rank=2, title="（趋势）末世+科幻", author="—",
                       genre="科幻", popularity=8800, word_count="—",
                       status="—", tags=["末世", "科幻", "生存"],
                       summary="末世文持续热门，结合科幻元素增长最快", source="knowledge"),
            RadarEntry(rank=3, title="（趋势）国风玄幻", author="—",
                       genre="仙侠", popularity=9200, word_count="—",
                       status="—", tags=["仙侠", "国风", "修炼"],
                       summary="国风玄幻是流量最大品类，新人入局门槛高", source="knowledge"),
            RadarEntry(rank=4, title="（趋势）悬疑+推理", author="—",
                       genre="悬疑", popularity=7800, word_count="—",
                       status="—", tags=["悬疑", "推理", "反转"],
                       summary="反转+快节奏的悬疑短篇在免费平台增长快", source="knowledge"),
            RadarEntry(rank=5, title="（趋势）系统流", author="—",
                       genre="都市", popularity=9500, word_count="—",
                       status="—", tags=["都市", "系统", "升级"],
                       summary="系统/游戏化框架仍是最大公约数题材", source="knowledge"),
        ]
