# GitHub InkEdge (RhythmicWave) 对比分析 · 改进参考

> 来源：https://github.com/RhythmicWave/NovelForge
> 分析日期：2026-05-24
> 状态：仅供后续版本迭代参考，不纳入当前 Phase 计划

---

## 一、概要

GitHub 上的 InkEdge 是另一个同名但完全不同的项目——全栈写作 IDE（Electron + Vue 3 + FastAPI + SQLModel + Neo4j），v0.9.5，已发布 Release 包。

本地 InkEdge 是管线引擎（Python + Streamlit + ChromaDB），Phase 1-12 开发中。

两者定位互补而非竞争。

---

## 二、核心思路借鉴（按优先级）

### 🔥 卡片数据模型（Card + Schema）

**GitHub 做法**：每种实体（角色/场景/章节/大纲/物品）都是一张"卡片"，有 JSON Schema 约束 AI 输出。所有数据通过 SQLModel 持久化。

**本地现状**：输出散落在 markdown/json 文件中（foundation.md / chapter_0001.md / summaries.json / state.json），无统一结构。

**改进方向**：定义 Card 基类 + Schema，Architect/Writer 输出结构化存储，替代纯文本。对 Phase 12 协议化有推动作用。

### 🔥 记忆层（Memory Layer / 6 实体提取器）

**GitHub 做法**（v0.9.4）：角色动态信息 / 关系提取入图 / 场景状态 / 组织状态 / 物品状态 / 概念掌握，每个实体类型独立 Extractor。统一"预览→确认→写入"流程。

**本地现状**：Phase 11 Observer 做一次性提取，无结构化预览确认。Phase 6 状态追踪仅覆盖角色。

**改进方向**：Observer 拆成 6 个专用 Extractor，每个实体类型独立提取逻辑。Phase 6 扩展到场景/物品/组织。

### 🔥 审核系统（Review System）

**GitHub 做法**：审核按钮 → 生成审核草稿 → 弹出预览 → 确认后保存为"审核结果卡片" → 历史可查。

**本地现状**：Phase 5 CheckOrchestrator one-shot 校验，结果写入文件，无审核历史。

**改进方向**：审核结果独立存储为结构化记录，支持历史回溯和多轮审核。

---

## 三、次要思路借鉴

### ⚡ 工作流 DSL

**GitHub 做法**：Python 风格 DSL 定义工作流（Logic.log / Logic.wait / Logic.async），Runner 执行，支持可视化编辑。

**本地现状**：Phase 之间硬编码顺序（Architect → Writer → ...），无 DSL 调度。

**改进方向**：Phase 12 协议化完成后，每个 Phase 就是工作流 Step，加 DSL 层自然演进为工作流系统。

### ⚡ 知识图谱（Relation Graph）

**GitHub 做法**：Neo4j + SQLite 存储角色-角色/角色-场景等关系三元组，前端可视化。

**本地现状**：Phase 11 CharacterSettler 在内存中构建交互矩阵，不持久化。

**改进方向**：SQLite 关系三元组表 + 简单网络图可视化。

---

## 四、暂不适用

- **流式 AI 生成**：需要重构 Writer 调用方式，改动太大
- **灵感助手 Agent**：独立对话系统，与本地 Agent 管线定位不同
- **Electron 打包**：Streamlit 够用
- **LLM 用量统计**：不急需

---

## 五、路线建议

```
v0.8 → 跑通端到端管线（new → write → check → settle → index）
v0.9 → Phase 10 doctor + Phase 12 协议化
v1.0 → 引入卡片模型 + 审核系统
v1.1 → 记忆层扩展（6实体提取器）
v1.2 → 知识图谱
v1.x → 工作流 DSL
```
