# 开源版/完整版 同步规则

> 最后更新: 2026-05-24

## 目录结构

```
InkEdge/          ← 完整版（私有，含完整类型知识 + 真实 API Key）
InkEdge_git/      ← 开源版（公开，骨架类型知识 + 占位符配置）
```

## 同步规则

### 双向同步（完全相同）

以下文件在两个仓库中**完全一致**，修改任一方后须同步到另一方：

```
src/agents/          (architect.py, writer.py, style_analyzer.py)
src/core/            (base_agent.py, context_budget.py, orchestrator.py)
src/governance/
src/prompts/
src/radar/           (base.py, agent.py, sources.py)
src/retrieval/       (vector_store.py, indexer.py, retriever.py)
src/settlement/      (observer.py, *settler.py, orchestrator.py)
src/state/           (manager.py, tracker.py, character_state.py)
src/utils/           (config.py, llm_client.py, file_io.py, text_utils.py,
                      context_builder.py, foundation_parser.py)
tests/               (全部测试文件)
pages/               (全部 Streamlit 页面)
main.py
studio.py
requirements.txt
```

### 单向同步（完整版→开源版，需处理）

以下文件在完整版中修改后，同步到开源版时需要做**降级处理**：

| 文件 | 降级规则 |
|------|---------|
| `config.yaml` | 替换 `api_key` 为占位符 `【在此填入你的API Key】` |
| `src/genre_knowledge/genres/*.py` | 替换为骨架版本（见下方规则） |

### 降级规则：genre_knowledge/genres/*.py

完整版 → 骨架版的降级原则：

1. **保留结构**：`GenreKnowledge(...)` 构造调用不变，字段名不变，`version` / `description` 不变
2. **缩减内容**：每个字段内容缩减为 2-4 句核心要点 + 末尾加免责声明
3. **免责声明**：每个缩减字段末尾追加 `（完整类型知识请使用 InkEdge 完整版）`
4. **urban.py 例外**：都市模块的完整版本身为常识级内容（~150字），**可直接完整开源**

降级对照：
| 字段 | 完整版 | 骨架版 |
|------|:--:|:--:|
| injection_text | 200-900字 | 50-120字 |
| naming_conventions | 40-180字 | 15-40字 |
| hierarchy_systems | 40-130字 | 15-40字 |
| world_rules | 30-120字 | 15-30字 |
| character_traits | 30-90字 | 15-30字 |
| plot_patterns | 30-110字 | 15-30字 |

### 不需要同步的内容

| 目录/文件 | 存在位置 | 说明 |
|----------|---------|------|
| `doc/` | 仅完整版 | Phase 设计文档，内部工程笔记 |
| `projects/` | 仅完整版 | 实际写作项目，含章节正文 |
| `config.yaml`（含真实 key） | 仅完整版 | 敏感数据 |
| `.pytest_cache/`, `__pycache__/` | 均不追踪 | 构建产物 |

### 同步流程

```
完整版修改代码
    ↓
git add + commit（InkEdge 仓库）
    ↓
判断是否涉及降级文件？
    ├── 否 → 直接复制到 InkEdge_git（或 cherry-pick）
    └── 是 → 先复制代码，再手动降级 genre/*.py 或 config.yaml
    ↓
git add + commit（InkEdge_git 仓库）
    ↓
git push（InkEdge_git → GitHub 公开仓库）
```

### 自动化脚本（待实现）

建议写一个 `sync_to_open_source.py` 脚本：

```python
# 伪代码
python sync_to_open_source.py
# 1. 复制非降级文件（src/ tests/ pages/ main.py 等）
# 2. 替换 config.yaml 中的 api_key
# 3. 降级 genre_knowledge/genres/*.py
# 4. 打印差异摘要
```
