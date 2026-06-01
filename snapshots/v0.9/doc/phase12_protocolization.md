# Phase 12 — 模块协议化改造

> 状态: 设计阶段 | 优先级: 中 | 预计测试: +30

## 背景

InkEdge 当前有 3 个模块存在硬编码扩展点：
- **ContextBuilder**: 上下文字段 + budget + build() 全部硬编码，每加一个来源要改 5 处
- **CheckOrchestrator**: 3 个检查器硬编码在 run() 里，if/else 链式调用
- **StateTracker**: 3 个状态维度（物品/能力/关系）硬编码，每个维度独立 dataclass + 解析逻辑

## 目标

为这 3 个模块定义标准协议，实现：
- 新增扩展点时不需修改现有模块代码
- 第三方可以按协议自行添加扩展，无需 fork
- 与已有的 `genre_knowledge/`、`radar/` 形成统一的可插拔架构风格

## 三个协议

### 1. ContextSource 协议 — 上下文来源可插拔

**位置**: `src/utils/context_source.py`

```python
class ContextSource(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def priority(self) -> int: ...    # 越小越靠前
    @property
    @abstractmethod
    def budget(self) -> int: ...      # 字数预算

    @abstractmethod
    def gather(self, project_dir: str, chapter_number: int, **ctx) -> str: ...
```

**改造范围**:
- `ChapterContext` dataclass → 改为动态字段（`sources: Dict[str, str]`）
- `ContextBuilder.build()` → 遍历 `self.sources` 按 priority 排序调用
- `build_prompt_context()` → 遍历 sources 按 budget 截断
- `CONTEXT_BUDGETS` 字典 → 每个 source 自带 budget

**内置 source 清单**（8个）:
| name | priority | budget | 来源 |
|------|:--:|:--:|------|
| story_frame | 1 | 2000 | foundation.md |
| volume_map | 2 | 1500 | file |
| roles | 3 | 3000 | file |
| book_rules | 4 | 500 | file |
| style_guide | 5 | 2000 | file |
| pending_hooks | 6 | 1000 | file |
| chapter_summaries | 7 | 2000 | 解析生成 |
| current_state | 8 | 500 | file |
| semantic_hits | 9 | 1500 | ChromaDB |
| genre_knowledge | 10 | 800 | KnowledgeLoader |

**日后扩展示例**:
```python
class MarketTrendSource(ContextSource):
    name = "market_trends"
    priority = 11
    budget = 600
    def gather(self, project_dir, chapter_number, **ctx):
        return self._fetch_latest_trends()
```

### 2. CheckProtocol — 校验器可插拔

**位置**: `src/validation/check_protocol.py`

```python
class CheckProtocol(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def weight(self) -> float: ...    # 报警权重 0.0-1.0

    @abstractmethod
    def check(self, chapter_text: str, **ctx) -> CheckResult: ...
```

**改造范围**:
- `CheckOrchestrator` → 构造函数改为 `checkers: List[CheckProtocol]`
- `run()` → 遍历 checkers 并行调用
- 移除 `skip_xxx` 参数 → 改为 `.disable("duplication")` 方法
- `CheckReport` → 改为动态 checkers 结果

**内置 checker 清单**（3个 → 可扩展）:
| name | weight | 功能 |
|------|:--:|------|
| duplication | 0.7 | 语义重复检测 |
| ai_style | 0.5 | AI 痕迹评分 |
| consistency | 0.8 | 前后一致性校验 |

**日后扩展示例**:
```python
class DialogueDensityChecker(CheckProtocol):
    name = "dialogue_density"
    weight = 0.3
    def check(self, chapter_text, **ctx):
        ratio = self._calc_dialogue_ratio(chapter_text)
        return CheckResult(passed=0.3 <= ratio <= 0.7, ...)
```

### 3. StateDimension 协议 — 状态维度可插拔

**位置**: `src/state/state_dimension.py`

```python
class StateDimension(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...        # "inventory" / "abilities" / "relationships"

    @abstractmethod
    async def extract(self, chapter_text: str, llm_client) -> List[dict]: ...

    @abstractmethod
    def apply(self, store: StateStore, changes: List[dict]) -> None: ...

    def format_display(self, store: StateStore) -> str: ...
```

**改造范围**:
- `StateTracker.track_changes()` → 遍历 `self.dimensions`
- 移除独立的 `InventoryChange` / `AbilityChange` / `RelationshipChange` dataclass → 统一为 `StateChange` dict
- `track()` 方法变为通用调度

**内置 dimension 清单**（3个）:
| name | 内容 |
|------|------|
| inventory | 物品获取/使用/丢失 |
| abilities | 技能学习/升级/使用 |
| relationships | 角色关系变化（好感度/阵营） |

**日后扩展示例**:
```python
class EmotionDimension(StateDimension):
    name = "emotions"
    async def extract(self, chapter_text, llm_client):
        return await llm_client.extract_emotions(chapter_text)
    def apply(self, store, changes):
        for c in changes:
            store.update_emotion(c["character"], c["emotion"], c["intensity"])
```

## 实施顺序

| 序号 | 协议 | 理由 |
|:--:|------|------|
| 1 | `ContextSource` | 扩展频率最高，每个新增功能都可能需要注入上下文 |
| 2 | `CheckProtocol` | 扩展频率中等，且改造改动量最小 |
| 3 | `StateDimension` | 扩展频率低，但改造可获得统一接口的整洁性 |

## 与已有可插拔模块的关系

```
InkEdge 可插拔体系（改造后）

  genre_knowledge/   ← KnowledgeLoader (已有)
  radar/             ← RadarSource + RadarAnalyzer + GenreKnowledgeBuilder (已有)
  prompts/           ← TemplateRegistry (已有)
  settlement/        ← Observer + N×Settler Orchestrator (已有)
  utils/             ← ContextSource 协议 (新增)
  validation/        ← CheckProtocol (新增)
  state/             ← StateDimension 协议 (新增)

统一风格:
  - 协议定义在模块内的 base.py 或独立 protocol 文件
  - 内置实现放在同一模块，第三方扩展放在外部
  - __init__.py 导出协议类 + 内置实现
```

## 测试计划

| 协议 | 测试文件 | 预计用例 |
|------|------|:--:|
| ContextSource | tests/test_phase12_context_source.py | 10 |
| CheckProtocol | tests/test_phase12_check_protocol.py | 10 |
| StateDimension | tests/test_phase12_state_dimension.py | 10 |
