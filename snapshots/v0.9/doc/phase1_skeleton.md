# Phase 1 — 项目骨架

> 状态：✅ 已完成（2026-05-23）
> 测试：6/6 通过

---

## 一、设计目标

搭建 InkEdge 的基础设施——目录结构、Agent 基类、编排器、上下文预算、LLM 客户端、文件 IO。这是所有后续 Phase 的地基。

---

## 二、架构设计

### 2.1 目录结构

```
InkEdge/
├── main.py                    # CLI 入口
├── config.yaml                # 全局配置
├── requirements.txt
├── src/
│   ├── core/                  # 核心框架
│   │   ├── base_agent.py      # Agent 抽象基类
│   │   ├── orchestrator.py    # 编排器（串行/并行/断点续传）
│   │   └── context_budget.py  # 上下文预算管理
│   ├── agents/                # 各 Agent 实现
│   ├── prompts/               # 提示词模板系统
│   ├── retrieval/             # 向量检索
│   ├── state/                 # 状态管理
│   ├── utils/                 # 工具模块
│   ├── governance/            # 治理/校验
│   └── validation/            # 后验校验
├── tests/
└── projects/                  # 用户项目目录
```

### 2.2 Agent 基类（base_agent.py）

**设计理念（来自 inkOS）：**

- 每个 Agent 是独立的"智能体"，有明确的职责边界
- Agent 之间通过 Orchestrator 编排，不直接通信
- 每个 Agent 有独立的 LLM 客户端配置（可不同模型/温度）
- 支持生命周期钩子：`setup() → run() → teardown()`

**核心数据结构：**

```python
AgentConfig     # 单个 Agent 的运行配置（模型/温度/token上限）
AgentContext    # Agent 间流转的共享状态（project_dir/foundation/summaries）
AgentResult     # Agent 执行结果（success/output/error/context_updates）
```

### 2.3 编排器（orchestrator.py）

```
Orchestrator
  ├─ run_sequential(steps, context)  → 顺序执行，可断点续传
  └─ run_parallel(steps, context)    → 并行执行（未来用途）

断点续传: 每步执行后保存 checkpoint，中断后从上次断点继续
```

### 2.4 上下文预算（context_budget.py）

来自 inkOS 的设计——不同类信息有不同的 token 预算上限：

```python
Budget = TokenCap × Priority
  story_frame:    优先级高，预算 2000 字
  writing_rules:  优先级中，预算 800 字
  summaries:      优先级低，预算 2000 字（超过截断）
```

### 2.5 LLM 客户端（llm_client.py）

**设计理念：**

适配任何 OpenAI 兼容 API，不绑定特定厂商。

**特性：**

- 同步/异步双接口（`chat()` / `chat_sync()`）
- 自动重试 + 指数退避
- 回退模型（主模型失败自动切换备选）
- Token 用量累计统计
- 温度/token上限可热切换

### 2.6 配置管理（config.py）

**三级优先级：**

```
环境变量 (DEEPSEEK_API_KEY) > config.yaml > 内置默认值
```

- 支持项目级配置覆盖（`projects/书名/config.yaml`）
- 敏感字段自动脱敏（mask_sensitive）
- 运行时热更新（`config.set(key, value)`）

---

## 三、关键设计决策

1. **异步优先**：`Agent.run()` 是 async，支持并行编排（虽然当前只用串行）
2. **断点续传**：Architect 每步用 `partial_architecture.json` 保存中间状态
3. **Agent 隔离**：Agent 间通过 AgentContext 通信，不直接互相调用
4. **Fallback 模型链**：主模型失败 → 回退模型 → 再失败才报错
5. **上下文预算**：从 inkOS 学来，按类型分预算 + 优先级裁剪，避免 prompt 爆炸

---

## 四、测试覆盖

```
test_imports          # 所有模块导入成功
test_base_agent       # Agent 基类实例化/配置/生命周期
test_context_budget   # Token 预算计算/优先级裁剪
test_file_io          # 原子写入/读取/目录创建
test_text_utils       # 文本清洗/分段/字数统计
test_cli_help         # CLI --help 正常输出
```

---

## 五、依赖

```
aiohttp         # 异步 HTTP（LLM 调用）
pyyaml          # 配置解析
chromadb        # 向量存储（Phase 4 用到，Phase 1 预留）
sentence-transformers  # 本地嵌入模型（Phase 4 用到）
```
