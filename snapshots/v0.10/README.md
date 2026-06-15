# InkEdge

> AI 辅助长篇小说创作框架 — Python 实现，inkOS 架构移植

## 致谢

InkEdge 的架构和设计理念来自以下两个优秀的开源项目：

- **[inkOS](https://github.com/actalk/inkos)**（@actalk/inkos v1.3.12）— AI 小说写作框架。InkEdge 的结算系统（Observer + 3 Settlers）、市场雷达、环境诊断、角色状态追踪等核心模块均移植自 inkOS 的设计，用 Python 重新实现。
- **[AI_NovelGenerator](https://github.com/fathah/AI_NovelGenerator)** — 多阶段 AI 小说生成器。InkEdge 的多阶段流水线思想（架构→规划→写作→校验→结算）受其启发。

站在巨人的肩膀上，感谢两位作者的开源贡献。

---

## 核心理念

写小说不是写一篇文章。它需要：

- **持久记忆**：角色状态、物品、关系、伏笔跨章节追踪
- **结算反思**：写完一章不是结束——Observer 提取事实，Settler 并行结算
- **质量控制**：重复检测、AI 痕迹评分、一致性校验
- **市场感知**：写之前知道读者在看什么

InkEdge 将这些理念落地为一个模块化的 Python 框架。

---

## 架构总览

```
                    ┌─────────┐
                   │  Architect │  ← Phase 2: 建书 (unified foundation)
                    └─────┬─────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
     ┌─────────┐    ┌──────────┐    ┌──────────┐
     │ Style   │    │  Writer  │    │ Knowledge│
     │ Guide   │    │ (Phase 3)│    │ (Phase 8)│
     └─────────┘    └────┬─────┘    └──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     ┌──────────┐  ┌──────────┐   ┌──────────┐
     │  Check   │  │  State   │   │Settlement│
     │(Phase 5) │  │(Phase 6) │   │(Phase 11)│  ← Observer+3 Settlers
     └──────────┘  └──────────┘   └──────────┘
                         │
                    ┌────┴────┐
                    │  Studio │  ← Phase 7: Streamlit GUI
                    └─────────┘
```

### Pipeline 流程

```
建书 → 风格分析 → 写稿 → 质量校验 → 角色状态更新 → 结算(Observer+3 Settlers)
  ↑                        ↓
  └──── 市场雷达(Phase 9) ←┘
                            ↓
                     下一章循环
```

---

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 建书

```bash
python main.py new --name "大宋秘谍" --topic "北宋穿越者发现前穿越者已点歪科技树，需刹车" --genre 历史架空 --chapters 360
```

### 写稿

```bash
python main.py write --name "大宋秘谍" --chapter 1 --guidance "沈安穿越醒来，发现自己附身在一个濒死的衙役身上"
```

### 校验

```bash
python main.py check --name "大宋秘谍" --chapter 1
```

### 结算（本章状态/角色/情节全面更新）

```bash
python main.py settle --name "大宋秘谍" --chapter 1
```

### 查看状态

```bash
python main.py status --name "大宋秘谍"     # 项目概览
python main.py state --name "大宋秘谍"       # 角色状态（物品/能力/关系）
```

---

## 模块地图

| Phase | 模块 | 路径 | 状态 |
|:-----:|------|------|:----:|
| 1 | 骨架 | `src/core/` | ✅ |
| 2 | Architect | `src/agents/architect.py` | ✅ |
| 3 | Writer | `src/agents/writer.py` | ✅ |
| 3.5 | Style | `src/governance/style/` | ✅ |
| 4 | 向量检索 | `src/retrieval/` | ✅ |
| 5 | 校验 | `src/validation/` | ✅ |
| 6 | 状态追踪 | `src/state/` | ✅ |
| 7 | GUI | `main.py studio` | ✅ |
| 8 | 知识注入 | `src/genre_knowledge/` | ✅ |
| 9 | 市场雷达 | `src/radar/` | ✅ |
| 10 | 环境诊断 | `src/doctor/` | ⏳ 设计阶段 |
| 11 | 结算系统 | `src/settlement/` | ✅ |
| 12 | 模块协议化 | `src/utils/` `src/validation/` `src/state/` | ⏳ 设计阶段 |

> 📋 完整开发路线图见 [ROADMAP.md](./ROADMAP.md)

---

## 项目结构

```
InkEdge/
├── main.py               # CLI 入口（所有命令统一入口）
├── config.yaml            # 用户配置
├── doc/                   # 设计文档
│   ├── phase1_skeleton.md       ~ phase12_protocolization.md
│   ├── sync_rules.md            # 开源版同步规则
│   └── ROADMAP.md               # 开发路线图（项目根目录）
├── src/                   # 核心模块
│   ├── core/              # Agent 基类、编排器、LLM 客户端、配置
│   ├── agents/            # Architect、Writer
│   ├── governance/        # 风格系统、模板注册
│   ├── retrieval/         # 向量检索（ChromaDB）
│   ├── validation/        # 后验校验
│   ├── state/             # 角色状态追踪
│   ├── settlement/        # 结算系统（Observer + 3 Settlers）
│   └── doctor/            # 环境诊断（Phase 10，待开发）
├── prompts/               # 提示词模板文件
├── projects/              # 书籍项目目录
│   └── <书名>/
│       ├── foundation/    # 统一基础设定
│       ├── story/
│       │   ├── state/     # 状态卡、情感弧线、伏笔池、支线面板、账本
│       │   └── outlines/  # 卷纲
│       ├── chapters/      # 章节正文
│       └── chroma_db/     # 向量索引
├── templates/             # 写作方法论模板
└── tests/                 # 测试（pytest）
```

---

## 配置

编辑 `config.yaml` 或通过环境变量设置：

```yaml
llm:
  provider: deepseek
  api_key: ${DEEPSEEK_API_KEY}
  base_url: https://api.deepseek.com/v1
  model: deepseek-v4-flash

paths:
  project_dir: projects/
```

支持 `.env` 文件中的 `DEEPSEEK_API_KEY`。

---

## 开发

```bash
# 运行全部测试
python -m pytest tests/ -q

# 运行特定模块测试
python -m pytest tests/test_phase11_settlement.py -v

# 环境诊断
python main.py doctor
```

### 架构规范

- **CLI 优先**：测试时直接调用 `python main.py <command>`，CLI 不可用才写诊断脚本
- **CLI/GUI 纯调度**：CLI 和 GUI 不含业务逻辑，只做参数解析/界面渲染，逻辑全部在 `src/`
- **双界面同步**：CLI 和 GUI 功能保持同步

---

## 许可证

MIT
