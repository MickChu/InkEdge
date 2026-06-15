# CLAUDE.md — InkEdge 开发指南

> 面向 AI 助手的项目上下文文档。包含架构决策、扩展接口、约定规范。

---

## 项目概览

InkEdge 是一个 AI 辅助长篇小说创作框架。将写作分解为多个独立阶段：
建书 → 风格分析 → 写稿 → 校验 → 状态追踪 → 结算 → 循环。

核心原则：每个阶段有明确的输入/输出、不越界、可独立测试。

---

## 关键路径

```
main.py              # CLI 入口（所有命令 → 纯调度，不含业务逻辑）
src/core/             # Agent 基类、LLM 客户端、配置系统、上下文预算
src/agents/           # Architect（建书）、Writer（写稿）
src/governance/       # 风格系统、模板注册
src/retrieval/        # ChromaDB 向量检索
src/validation/       # 后验校验（重复/AI痕迹/一致性）
src/state/            # 角色状态追踪（物品/能力/关系）
src/settlement/       # 结算系统（Observer + 3 Settlers）
prompts/              # 提示词模板
templates/            # 写作方法论模板
```

---

## 扩展接口

### 1. 模板注册 (Phase 2)

```python
from src.governance.base_template import TemplateRegistry, PromptTemplateSet

registry = TemplateRegistry()
registry.register(my_template_set)  # PromptTemplateSet 实例
```

模板集需实现 `PromptTemplateSet` 接口：
- `name: str` — 模板集名称
- `steps: List[PromptStep]` — 步骤列表
- `build_prompt(step, context) -> str` — 生成提示词

**当前内置**: `snowflake` (雪花法), `unified` (inkOS 风格)

---

### 2. 类型知识注入 (Phase 8 设计，待实现)

```python
from src.genre_knowledge.base import GenreKnowledgeSource

class WuxiaKnowledge(GenreKnowledgeSource):
    name = "武侠"
    version = "1.0"

    def inject_architect(self, prompt: str) -> str: ...
    def inject_writer(self, prompt: str) -> str: ...
```

注册方式：
```python
from src.genre_knowledge.registry import GenreRegistry
GenreRegistry.register(WuxiaKnowledge())
```

---

### 3. 市场雷达数据源 (Phase 9 设计，待实现)

```python
from src.radar.sources import RadarSource

class MyRadarSource(RadarSource):
    async def fetch(self) -> List[RadarEntry]: ...
    def offline_fallback(self) -> List[RadarEntry]: ...
```

已设计：`FanqieRadarSource`, `QidianRadarSource`, `KnowledgeRadarSource`

---

### 4. 结算 Settler 扩展 (Phase 11)

结算系统采用 Observer → N×Settler 架构。新增 Settler 只需：

```python
from src.settlement.orchestrator import SettlementOrchestrator

# 1. 实现 settler，包含 async settle() 和 _read/_save 模式
# 2. 在 SettlementOrchestrator.settle() 中添加到 asyncio.gather 列表
```

当前 Settler 三件套：
- `WorldSettler` → 状态卡 + 资源账本
- `CharacterSettler` → 情感弧线 + 角色交互矩阵
- `PlotSettler` → 伏笔池 + 章节摘要 + 支线面板

---

### 5. LLM 客户端配置

```python
from src.core.llm_client import LLMClient

llm = LLMClient()
# 自动读取 config.yaml 中的 llm 节
# 支持 DeepSeek / OpenAI / 兼容 API
```

配置 (`config.yaml`):
```yaml
llm:
  provider: deepseek
  api_key: ${DEEPSEEK_API_KEY}
  base_url: https://api.deepseek.com/v1
  model: deepseek-v4-flash
```

---

## 项目文件约定

每本书的目录结构：

```
projects/<书名>/
├── foundation/           # Architect 输出
│   └── unified_foundation.md
├── story/
│   ├── state/            # 结算系统输出
│   │   ├── current_state.md        # WorldSettler
│   │   ├── ledger.md               # WorldSettler
│   │   ├── emotional_arcs.md       # CharacterSettler
│   │   ├── character_matrix.md     # CharacterSettler
│   │   ├── hooks.md                # PlotSettler
│   │   └── subplots.md             # PlotSettler
│   └── outlines/
│       └── volume_01.md
├── chapters/
│   └── 0001.md, 0002.md, ...
├── chapter_summaries.md  # PlotSettler 输出
├── style_guide.md        # Phase 3.5 输出
├── current_state.md      # Phase 6 StateManager 输出
└── chroma_db/            # Phase 4 向量索引
```

---

## 开发约定

1. **CLI 优先测试**：`python -m pytest tests/test_<module>.py -v`
2. **CLI/GUI 纯调度**：CLI 和 GUI 不含业务逻辑，逻辑全部在 `src/`
3. **模块自足**：每个 `src/` 子模块可独立导入和测试
4. **LLM 回退**：所有 LLM 调用必须有正则/规则回退路径

---

## 当前状态

| Phase | 模块 | 状态 |
|-------|------|------|
| 1 | 骨架 | ✅ |
| 2 | Architect | ✅ |
| 3 | Writer | ✅ |
| 3.5 | Style | ✅ |
| 4 | 向量检索 | ✅ |
| 5 | 校验 | ✅ |
| 6 | 状态追踪 | ✅ |
| 7 | GUI | 📋 设计已完成 |
| 8 | 类型知识 | 📋 设计已完成 |
| 9 | 市场雷达 | 📋 设计已完成 |
| 10 | 环境诊断 | 📋 设计已完成 |
| 11 | 结算系统 | ✅ |

全部 69 测试通过。
