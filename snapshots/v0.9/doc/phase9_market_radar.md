# Phase 9 — 市场雷达（Market Radar）

> 版本：0.1（设计稿）
> 日期：2026-05-24
> 状态：设计阶段
> 来源：inkOS 同名功能

---

## 一、问题定义

### 1.1 当前痛点

用户在 `python main.py new --topic "……" --genre 奇幻` 时，选题完全依赖直觉。他不知道：
- 奇幻这个大类型下，什么子方向正在上升
- 番茄/起点当前热榜上扎堆了哪些题材
- 什么方向是蓝海（有读者需求但缺好作品）

### 1.2 市场雷达做什么

在建书前扫一眼市场——不是让 AI 替用户决定写什么，而是提供**有数据支撑的决策参考**。

---

## 二、设计理念

### 2.1 核心原则

1. **数据驱动**：不依赖 LLM 训练数据（可能是几个月前的），而是实时抓取排行榜
2. **建议不决策**：雷达只给趋势分析+概念建议，最终选题永远由用户决定
3. **可插拔数据源**：番茄/起点是内置源，用户可添加自定义源
4. **离线可降级**：如果网络不通（老板可能用纯离线模式），降级为 LLM 基于训练数据的分析
5. **存档可追溯**：每次扫描结果存档，方便回溯决策依据

### 2.2 数据流

```
网络爬虫/API
  │
  ├─→ 番茄小说 (热门榜 + 黑马榜)
  ├─→ 起点中文网 (热榜 HTML 解析)
  └─→ (可选) 自定义数据源
        │
        ▼
  排行榜数据 (结构化)
        │
        ▼
  MarketRadarAgent (LLM 分析)
        │
        ▼
  市场报告 → radar/scan-{timestamp}.json
            → CLI 输出
            → 可传递到 Architect 的 guidance
```

---

## 三、数据结构

### 3.1 排行榜条目

```python
@dataclass
class RankingEntry:
    title: str               # 书名
    author: str = ""         # 作者
    category: str = ""       # 分类/标签
    extra: str = ""          # 附加信息（如"[热门榜]""[新书榜]"）
```

### 3.2 平台排行榜

```python
@dataclass 
class PlatformRankings:
    platform: str                        # 平台名（"番茄小说""起点中文网"）
    entries: List[RankingEntry]          # 排行榜条目
```

### 3.3 市场分析结果

```python
@dataclass
class RadarRecommendation:
    platform: str              # 建议发布的平台
    genre: str                 # 建议的题材
    concept: str               # 一句话概念描述
    confidence: float          # 置信度 0-1
    reasoning: str             # 推荐理由（引用榜单数据）
    benchmark_titles: List[str]  # 对标作品

@dataclass
class RadarResult:
    recommendations: List[RadarRecommendation]
    market_summary: str          # 整体市场概述
    timestamp: str               # ISO 扫描时间
```

---

## 四、数据源设计

### 4.1 番茄小说源

```python
class FanqieRadarSource:
    """番茄小说排行榜数据源"""
    
    RANK_TYPES = [
        {"sideType": 10, "label": "热门榜"},
        {"sideType": 13, "label": "黑马榜"},
    ]
    
    async def fetch(self) -> PlatformRankings:
        for rank_type in self.RANK_TYPES:
            url = f"https://api-lf.fanqiesdk.com/api/novel/channel/homepage/rank/rank_list/v2/"
            # params: aid=13, limit=15, side_type={sideType}
            # 解析: book_name, author, category
```

### 4.2 起点中文网源

```python
class QidianRadarSource:
    """起点中文网排行榜数据源"""
    
    async def fetch(self) -> PlatformRankings:
        # GET https://www.qidian.com/rank/
        # HTML 正则提取书名
        # pattern: /<a[^>]*href="\/\/book\.qidian\.com\/info\/(\d+)"[^>]*>([^<]+)<\/a>/
```

### 4.3 自定义源接口

```python
class RadarSource(ABC):
    """可插拔数据源接口"""
    name: str
    
    @abstractmethod
    async def fetch(self) -> PlatformRankings:
        ...
```

### 4.4 离线降级源

```python
class KnowledgeRadarSource(RadarSource):
    """当网络不可用时，使用 LLM 训练知识作为备选"""
    name = "knowledge"
    
    async def fetch(self) -> PlatformRankings:
        # 返回空排行榜 → MarketRadarAgent 会基于训练数据分析
        return PlatformRankings(platform="LLM知识", entries=[])
```

---

## 五、MarketRadarAgent

### 5.1 分析流程

```python
class MarketRadarAgent(BaseAgent):
    """市场雷达 Agent"""
    
    async def scan(self, platforms: List[str] | None = None) -> RadarResult:
        # 1. 并行抓取所有数据源
        rankings = await self._fetch_all(platforms)
        
        # 2. 组装分析 prompt
        prompt = self._build_analysis_prompt(rankings)
        
        # 3. LLM 分析市场趋势
        response = await self.chat(prompt)
        
        # 4. 解析 JSON 结果
        return self._parse_result(response.content)
```

### 5.2 分析 Prompt 核心结构

```
你是一个专业的网络小说市场分析师。
下面是各平台实时抓取的排行榜数据。

## 实时排行榜数据

### 番茄小说
- 书名A (作者X) [热门榜]
- 书名B (作者Y) [黑马榜]
...

### 起点中文网
- 书名C [起点热榜]
...

分析维度：
1. 从排行榜识别当前热门题材和标签
2. 哪些类型占据榜单高位
3. 市场空白和机会点
4. 风险提示（过度扎堆的题材）

输出 JSON：{ recommendations: [...], marketSummary: "..." }
```

---

## 六、与 Architect 的集成

建书时可选传入市场分析结果，作为 bias 影响选题方向。

### 6.1 新建项目时自动询问

```bash
$ python main.py new --name "我的小说" --topic "修仙"

📡 是否先进行市场扫描？(y/n, 默认 n): y

🔍 扫描中...
  番茄小说: 30 条
  起点中文网: 20 条

📊 市场分析:
  热门题材: 都市异能(↑12%), 洪荒流(↑8%), 传统修仙(↓5%)
  💡 机会: 修仙+科幻融合方向缺优质作品
  ⚠️ 风险: 纯升级流严重饱和

  基于你的 topic "修仙" 的建议:
    - 加入科幻元素差异化的置信度较高(82%)
    - 建议避免纯升级打怪路线

  是否按此建议调整？(直接回车 = 接受，输入新 topic = 覆盖):
```

### 6.2 雷达结果自动注入 Architect

如果用户做了市场扫描，扫描结果自动写入 `AgentContext.extra["market_analysis"]`，Architect 在生成 unified foundation 时参考。

---

## 七、CLI 设计

```bash
# 全平台扫描
python main.py radar

# 只扫指定平台
python main.py radar --platforms fanqie,qidian

# 离线模式（只用 LLM 知识）
python main.py radar --offline

# JSON 输出（供脚本调用）
python main.py radar --json

# 查看历史扫描
python main.py radar --history

# 查看某次扫描详情
python main.py radar --load scan-2026-05-24T06-00-00.json
```

---

## 八、文件结构

```
src/radar/
├── __init__.py
├── agent.py                # MarketRadarAgent
├── sources.py              # FanqieRadarSource / QidianRadarSource / KnowledgeRadarSource
├── models.py               # RadarResult / RadarRecommendation / RankingEntry
└── cli.py                  # CLI 命令集成

projects/书名/radar/        # 市场扫描存档
└── scan-{timestamp}.json
```

---

## 九、未来改进方向

### 9.1 更多数据源（v1.1）

- 飞卢小说网、七猫、晋江等平台
- 抖音/微博小说话题热度（社交媒体信号）
- 各平台编辑推荐方向（官方信号）

### 9.2 趋势追踪（v1.2）

不只是单次扫描，而是追踪题材的涨跌趋势：

```
都市异能:  ████████░░  +12% (本月)  → 上升中
传统修仙:  ████░░░░░░  -5%  (本月)   → 下降中
```

### 9.3 作品定位建议（v2.0）

结合市场数据和用户的 style guide，给出完整的作品定位方案：
- 目标读者画像
- 差异化卖点
- 对标作品 + 差异化策略
- 预期数据（收藏/追读范围）

### 9.4 GUI 市场面板

在 Streamlit GUI 中展示可视化市场仪表盘（Stage 7 集成）。

---

## 十、决策记录

- **2026-05-24**：从 inkOS 市场雷达功能移植设计。数据源架构与 inkOS 一致（FanqieRadarSource + QidianRadarSource + 可插拔接口）。
- 设计选择：新增独立 Phase 9，因为它是建书前的可选工具，不影响现有核心链路。
- 离线降级策略：网络不通时用 KnowledgeRadarSource，LLM 基于训练知识给分析，并在输出中标注"⚠️ 离线模式，基于模型训练数据而非实时排行榜"。
