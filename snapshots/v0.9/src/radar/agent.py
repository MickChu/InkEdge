"""
RadarAgent — LLM 趋势分析器

实现 RadarAnalyzer 协议: scan / identify_trends / cluster_genres
"""
import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict

from .base import (
    RadarSource, RadarReport, TrendReport, GenreCluster,
    RadarAnalyzer, GenreKnowledgeBuilder,
)


# ── Prompt 模板 ────────────────────────────────────────

RADAR_SYSTEM_PROMPT = """你是网文市场分析专家。根据排行榜数据，分析当前市场趋势并给出开书建议。

## 分析要求

1. **趋势总结**（2-3句）：当前市场上什么类型最热、什么在上升、什么在下降
2. **热门标签**（3-5个）：重复出现的关键标签/主题
3. **趋势洞察**（3-5条）：
   - 题材风向：什么题材读者在追
   - 写作特征：热门书的结构/节奏/字数特点
   - 新人机会：哪些细分品类竞争较小
   - 雷区：哪些元素读者已经审美疲劳
4. **开书建议**（3-5条）：
   - 建议题材方向
   - 差异化切入点
   - 目标读者画像
   - 字数/更新策略

## 输出格式

=== TREND_SUMMARY ===
(2-3句趋势总结)

=== HOT_TAGS ===
- 标签1

=== TREND_INSIGHTS ===
- 洞察1

=== WRITING_ADVICE ===
- 建议1"""


RADAR_USER_PROMPT = """请分析以下排行榜数据，提供市场趋势和开书建议。

分析类型: {genre}（为"全榜"时分析整体趋势）

## 排行榜数据
{data_block}

请严格按照 === TAG === 格式输出。"""


TREND_CLASSIFY_PROMPT = """你是网文分类学专家。分析以下平台原始分类，识别当前市场中**上升趋势**和**下降趋势**的品类。

## 分析要求

对每个分类判断：上升(rising)、下降(declining)、稳定(stable)
- 上升: 近期有新爆款、高增长、跨界作品涌入
- 下降: 同质化严重、读者疲劳、高开低走
- 稳定: 经典品类、基础盘稳固、波动小

## 输出格式

=== SUMMARY ===
(一句话总览)

=== RISING ===
- 分类名 | 置信度0.0-1.0 | 依据

=== DECLINING ===
- 分类名 | 置信度0.0-1.0 | 依据

=== STABLE ===
- 分类名 | 置信度0.0-1.0 | 依据"""


GENRE_CLUSTER_PROMPT = """你是小说品类体系设计师。

当前 InkEdge 内置 6 个创作品类:
{current_genres}

下面是 {source} 平台的原始分类:
{platform_categories}

## 任务

1. **归并**：把平台分类逐一映射到最接近的内置品类，给出置信度
2. **发现缺口**：找出 6 个内置品类完全覆盖不了的平台分类
3. **建议新建**：从缺口中挑出"值得单独建模块"的（市场体量大 + 写作惯例明显不同）

## 输出格式

=== MAPPING ===
平台分类 → 内置品类 | 置信度
玄幻 → 奇幻 | 0.85
...

=== UNCOVERED ===
- 分类名 | 理由

=== SUGGESTED_NEW ===
- 分类名 | 理由（市场体量/独特性）"""


# ── 类型知识自动生成 Prompt ─────────────────────────

KNOWLEDGE_GEN_PROMPT = """你是网文品类学专家。请为以下品类生成类型知识模块：

品类: {genre}
市场趋势: {trends_summary}

## 输出内容

1. **写作惯例**（200-400字）: 该品类约定俗成的写作规则、读者期待
2. **命名体系**（100-200字）: 角色名/地名/招式名的命名规律
3. **等级/战力体系**（150-300字）: 该品类特有的力量阶梯或成长体系
4. **角色原型**（150-300字）: 该品类常见主角/反派/配角模板
5. **情节模式**（150-300字）: 该品类常用的叙事套路和节奏

## 输出格式

=== INJECTION_TEXT ===
...

=== NAMING_CONVENTIONS ===
...

=== HIERARCHY_SYSTEMS ===
...

=== CHARACTER_ARCHETYPES ===
...

=== PLOT_PATTERNS ===
..."""


# ── RadarAgent ────────────────────────────────────────

class RadarAgent(RadarAnalyzer):
    """市场雷达分析器 — 实现 RadarAnalyzer 协议"""

    def __init__(self, sources: Optional[List[RadarSource]] = None):
        self.sources = sources or []

    def add_source(self, source: RadarSource):
        self.sources.append(source)

    # ── scan() ──────────────────────────────────────

    async def scan(self, genre: str = "", limit: int = 30,
                   llm_client=None) -> TrendReport:
        reports = await self._fetch_all(genre, limit)
        data_block = self._format_entries(reports)

        trend = TrendReport(
            genre=genre or "全榜",
            raw_entries_count=sum(len(r.entries) for r in reports),
            sources=[r.source for r in reports],
        )

        if llm_client:
            prompt = RADAR_USER_PROMPT.format(genre=genre or "全榜", data_block=data_block[:6000])
            try:
                resp = await llm_client.chat(
                    prompt=prompt, system_prompt=RADAR_SYSTEM_PROMPT,
                    temperature=0.5, max_tokens=2000,
                )
                trend = self._parse_scan(resp.content, trend)
            except Exception:
                pass

        if not trend.summary:
            trend.summary = f"已扫描 {trend.raw_entries_count} 条数据，来自 {', '.join(trend.sources)} (LLM 暂不可用)"

        return trend

    # ── identify_trends() ───────────────────────────

    async def identify_trends(self, genre: str = "", limit: int = 30,
                              llm_client=None) -> dict:
        """
        识别上升/下降品类。

        Returns:
            {rising: [...], declining: [...], stable: [...], summary: "..."}
        """
        reports = await self._fetch_all(genre, limit)
        data_block = self._format_entries(reports, compact=True)

        result = {"rising": [], "declining": [], "stable": [], "summary": ""}

        if llm_client:
            prompt = f"当前排行榜数据:\n{data_block[:5000]}\n\n请严格按 === TAG === 格式输出。"
            try:
                resp = await llm_client.chat(
                    prompt=prompt, system_prompt=TREND_CLASSIFY_PROMPT,
                    temperature=0.3, max_tokens=1500,
                )
                result = self._parse_trends(resp.content)
            except Exception:
                pass

        if not result["summary"]:
            result["summary"] = f"从 {result.get('_entries', 0)} 条数据中识别趋势 (LLM 暂不可用)"

        return result

    # ── cluster_genres() ────────────────────────────

    async def cluster_genres(self, source: str = "all",
                             llm_client=None) -> GenreCluster:
        """
        分析平台分类体系 → 归并到现有6类的方案。

        Args:
            source: fanqie / qidian / all
        """
        source_map = {
            "fanqie": self._fanqie_categories,
            "qidian": self._qidian_categories,
            "all": lambda: self._fanqie_categories() + self._qidian_categories(),
        }
        cats = source_map.get(source, source_map["all"])()
        cat_str = "\n".join(f"- {c}" for c in cats)

        current = self._current_genre_list()
        current_str = "\n".join(f"- {n}: {d}" for n, d in current)

        cluster = GenreCluster(
            source=source,
            uncovered=[],
            suggested_new=[],
        )

        if llm_client:
            prompt = GENRE_CLUSTER_PROMPT.format(
                current_genres=current_str,
                source=source,
                platform_categories=cat_str,
            )
            try:
                resp = await llm_client.chat(
                    prompt=prompt, system_prompt="你是严谨的分类学专家。",
                    temperature=0.2, max_tokens=2000,
                )
                cluster = self._parse_cluster(resp.content, cluster)
            except Exception:
                pass

        # fallback: 基于规则的基本映射
        if not cluster.clusters:
            cluster = self._rule_based_cluster(cats, cluster)

        return cluster

    # ── 内部 helpers ────────────────────────────────

    async def _fetch_all(self, genre: str, limit: int) -> List[RadarReport]:
        if not self.sources:
            from .sources import KnowledgeRadarSource
            self.sources = [KnowledgeRadarSource()]

        tasks = [s.fetch(genre, limit) for s in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        reports = []
        for r in results:
            if isinstance(r, RadarReport):
                reports.append(r)
            # fetch 内部已经降级，这里只是保险
        return reports or [self.sources[0].offline_fallback(genre, limit)]

    def _format_entries(self, reports: List[RadarReport], compact: bool = False) -> str:
        lines = []
        for r in reports:
            lines.append(f"## {r.source} ({r.note or '实时'})")
            for e in r.entries:
                if compact:
                    lines.append(f"{e.rank}. {e.title} | {e.genre} | 人气{e.popularity}")
                else:
                    tags_str = ", ".join(e.tags) if e.tags else ""
                    lines.append(
                        f"{e.rank}. {e.title} | {e.author} | {e.genre} | "
                        f"人气{e.popularity} | {e.word_count}字 | {e.status}"
                    )
                    if tags_str:
                        lines.append(f"   标签: {tags_str}")
            lines.append("")
        return "\n".join(lines)

    def _parse_scan(self, content: str, base: TrendReport) -> TrendReport:
        def extract(tag: str) -> str:
            m = re.search(rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)", content)
            return m.group(1).strip() if m else ""

        base.summary = extract("TREND_SUMMARY")
        base.hot_tags = [t.strip("- ") for t in extract("HOT_TAGS").split("\n") if t.strip()]
        base.trend_insights = extract("TREND_INSIGHTS")
        base.writing_advice = extract("WRITING_ADVICE")
        return base

    def _parse_trends(self, content: str) -> dict:
        def extract(tag: str) -> str:
            m = re.search(rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)", content)
            return m.group(1).strip() if m else ""

        def parse_items(text: str) -> list:
            items = []
            for line in text.split("\n"):
                line = line.strip("- ")
                if not line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    items.append({
                        "category": parts[0],
                        "confidence": float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 0.5,
                        "evidence": parts[2] if len(parts) > 2 else "",
                    })
            return items

        return {
            "rising": parse_items(extract("RISING")),
            "declining": parse_items(extract("DECLINING")),
            "stable": parse_items(extract("STABLE")),
            "summary": extract("SUMMARY"),
        }

    def _parse_cluster(self, content: str, base: GenreCluster) -> GenreCluster:
        mapping_text = self._extract_section(content, "MAPPING")
        uncovered_text = self._extract_section(content, "UNCOVERED")
        suggested_text = self._extract_section(content, "SUGGESTED_NEW")

        clusters = []
        for line in mapping_text.split("\n"):
            line = line.strip("- ")
            if "→" not in line:
                continue
            parts = [p.strip() for p in line.split("→")]
            if len(parts) < 2:
                continue
            platform_genre = parts[0]
            rest = parts[1].split("|")
            mapped_to = rest[0].strip()
            confidence = float(rest[1].strip()) if len(rest) > 1 and rest[1].strip().replace(".", "").isdigit() else 0.7
            clusters.append({
                "platform_category": platform_genre,
                "mapped_to": mapped_to,
                "confidence": confidence,
            })

        uncovered = [line.strip("- ") for line in uncovered_text.split("\n") if line.strip()]
        suggested = [line.strip("- ").split("|")[0].strip() for line in suggested_text.split("\n") if line.strip()]

        base.clusters = clusters or base.clusters
        base.uncovered = uncovered or base.uncovered
        base.suggested_new = suggested or base.suggested_new
        return base

    def _rule_based_cluster(self, cats: List[str], base: GenreCluster) -> GenreCluster:
        """无 LLM 时的规则回退"""
        mapping = {
            "玄幻": "奇幻", "奇幻": "奇幻", "仙侠": "奇幻",
            "武侠": "武侠",
            "都市": "都市", "现实": "都市", "轻小说": "都市",
            "科幻": "科幻", "末世": "科幻", "游戏": "科幻",
            "悬疑": "悬疑", "灵异": "悬疑", "恐怖": "悬疑",
            "历史": "历史", "军事": "历史", "古代": "历史",
            "体育": "都市", "电竞": "科幻",
        }
        clusters = []
        for cat in cats:
            clean = cat.strip()
            mapped = mapping.get(clean, "其他")
            clusters.append({
                "platform_category": clean,
                "mapped_to": mapped,
                "confidence": 0.5 if mapped == "其他" else 0.7,
            })
        base.clusters = clusters
        base.uncovered = [c for c in cats if mapping.get(c.strip(), "其他") == "其他"]
        return base

    @staticmethod
    def _extract_section(content: str, tag: str) -> str:
        m = re.search(rf"=== {tag} ===\s*([\s\S]*?)(?==== [A-Z_]+\s*===|$)", content)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _current_genre_list() -> list:
        from importlib import import_module
        try:
            from src.genre_knowledge import KnowledgeLoader
            loader = KnowledgeLoader()
            return [(k, v) for k, v in loader.list_all().items()]
        except Exception:
            return [
                ("wuxia", "武侠"), ("scifi", "科幻"), ("urban", "都市"),
                ("mystery", "悬疑"), ("fantasy", "奇幻"), ("historical", "历史"),
            ]

    @staticmethod
    def _fanqie_categories() -> List[str]:
        return [
            "都市", "玄幻", "仙侠", "历史", "科幻", "游戏",
            "军事", "灵异", "武侠", "末世", "悬疑", "轻小说",
        ]

    @staticmethod
    def _qidian_categories() -> List[str]:
        return [
            "玄幻", "奇幻", "武侠", "仙侠", "都市", "现实",
            "军事", "历史", "游戏", "体育", "科幻", "悬疑",
            "灵异", "轻小说", "二次元", "短篇",
        ]


# ── GenreKnowledgeBuilderStub ─────────────────────────

class GenreKnowledgeBuilderStub(GenreKnowledgeBuilder):
    """
    类型知识自动生成器 — 预留接口。

    日后实现完整的 LLM 驱动模块生成，当前返回协议约定的格式。
    """

    async def from_radar_data(self, trends: dict, genre: str, llm_client=None) -> dict:
        draft = {
            "genre": genre,
            "display_name": genre,
            "injection_text": "",
            "naming_conventions": "",
            "hierarchy_systems": "",
            "character_archetypes": "",
            "plot_patterns": "",
            "draft_path": f"src/genre_knowledge/genres/{genre}.py",
            "needs_review": True,
        }

        if llm_client:
            trends_summary = trends.get("summary", "")[:500]
            prompt = KNOWLEDGE_GEN_PROMPT.format(genre=genre, trends_summary=trends_summary)
            try:
                resp = await llm_client.chat(
                    prompt=prompt,
                    system_prompt="你是网文品类学专家，输出严谨专业的模块内容。",
                    temperature=0.4, max_tokens=3000,
                )
                draft.update(self._parse_knowledge(resp.content, genre))
            except Exception:
                pass

        return draft

    def validate_module(self, draft: dict) -> list:
        checks = []
        for field in ["injection_text", "naming_conventions", "hierarchy_systems",
                       "character_archetypes", "plot_patterns"]:
            content = draft.get(field, "")
            passed = len(content) > 50
            checks.append({
                "check": field,
                "passed": passed,
                "note": f"{'✅' if passed else '⚠️'} 内容{'充足' if passed else '不足'} ({len(content)} 字符)",
            })
        return checks

    def _parse_knowledge(self, content: str, genre: str) -> dict:
        return {
            "injection_text": RadarAgent._extract_section(content, "INJECTION_TEXT"),
            "naming_conventions": RadarAgent._extract_section(content, "NAMING_CONVENTIONS"),
            "hierarchy_systems": RadarAgent._extract_section(content, "HIERARCHY_SYSTEMS"),
            "character_archetypes": RadarAgent._extract_section(content, "CHARACTER_ARCHETYPES"),
            "plot_patterns": RadarAgent._extract_section(content, "PLOT_PATTERNS"),
            "draft_path": f"src/genre_knowledge/genres/{genre}.py",
            "needs_review": True,
        }
