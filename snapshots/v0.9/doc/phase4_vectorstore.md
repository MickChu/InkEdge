# Phase 4 — VectorStore（向量检索）

> 状态：✅ 已完成（2026-05-23）
> 测试：22/22 通过
> 最近更新：2026-05-24 完成纯离线改造

---

## 一、设计目标

ContextBuilder 的线性摘要只能提供"最近 5 章发生了什么"。但当写第 30 章时，第 3 章的一个细节可能很重要——语义搜索引擎让 Writer 能跨越时间线找到最相关的内容。

---

## 二、工作原理

```
┌─ 离线阶段：索引 ──────────────────────────┐
│                                            │
│  小说内容  →  分块  →  嵌入模型  →  向量   │
│  (foundation  (500字/块)  (本地模型)  (存库) │
│   chapters                               │
│   hooks)                                  │
│                                            │
└────────────────────────────────────────────┘

┌─ 在线阶段：检索 ──────────────────────────┐
│                                            │
│  Writer问: "破庙 记忆替换"                  │
│      ↓                                     │
│  同样嵌入成向量                             │
│      ↓                                     │
│  ChromaDB 余弦相似度搜索                    │
│      ↓                                     │
│  返回最相关的 5 条原文                      │
│                                            │
└────────────────────────────────────────────┘
```

关键区别：不是关键词匹配（"破庙"必须出现），而是**语义匹配**（"主角失忆那个场景"能命中"沈安在破庙醒来，记忆又被替换了"）。

---

## 三、三大组件

### 3.1 VectorStore（存储层）

**技术栈：**

```
ChromaDB          # 向量数据库，本地持久化
  + sentence-transformers  # 本地嵌入模型
      └─ paraphrase-multilingual-MiniLM-L12-v2
         维度: 384
         大小: 470MB
         加载: ~14s (CPU, 纯磁盘I/O)
         编码: 0.2s/条
```

**纯离线保证（2026-05-24 改造）：**

```python
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 禁止联网检查

SentenceTransformerEmbeddingFunction(
    model_name="...",
    device="cpu",
    local_files_only=True,   # 只用本地缓存
)
```

第一次初始化时 `sentence-transformers` 默认去 `huggingface.co` 检查模型更新。如果网络不通，会反复重试卡死。加这两行后彻底禁止联网，纯磁盘加载。

**Collections（数据分组）：**

| Collection | 存储内容 | 来源 |
|------------|----------|------|
| foundations | story_frame / roles / book_rules 分块 | 建书时生成 |
| chapters | 章节摘要 + 每章前800后200字 | 写完后增量 |
| hooks | pending_hooks 中的每条伏笔 | 建书时生成 |

### 3.2 DocumentIndexer（索引层）

**全量索引流程：**

```python
DocumentIndexer(store).index_project(project_dir):
  1. 读取 story_frame.md / roles.md / book_rules.md
  2. 每个文件分块（500字/块，100字重叠）
  3. 写入 foundations collection
  
  4. 读取 chapter_summaries.md
  5. 每行解析为单独摘要文档
  6. 同时读取 chapters/ 下的正文（每章前800+后200字）
  7. 写入 chapters collection
  
  8. 读取 pending_hooks.md
  9. 解析 hook 标记，每个钩子单独索引
  10. 写入 hooks collection
```

**增量索引：**

新章节写完后，只索引这一章的摘要：

```python
DocumentIndexer(store).index_new_chapter(project_dir, ch_num, summary)
```

### 3.3 SemanticRetriever（检索层）

**检索流程：**

```python
retriever = SemanticRetriever(store)
results = retriever.retrieve_for_chapter(
    chapter_number=4,
    query="沈安进入天听阁废墟",
    n_results=5,
)
```

**多 Collection 联合检索：**

对 foundations、chapters、hooks 三个 collection 分别 query，合并后按相似度排序，返回 top-k。

**查询构建：**

不只是用户输入的纯文本，而是结合当前章节信息构建更精准的查询：

```python
def build_query(self, chapter_number, context):
    parts = []
    if context.get("user_guidance"):
        parts.append(context["user_guidance"])
    if context.get("current_state"):
        parts.append(context["current_state"])
    if context.get("hook_check"):  # 检查哪些伏笔该收
        parts.append("伏笔回收")
    return " ".join(parts)
```

---

## 四、与 ContextBuilder 的集成

ContextBuilder 在构建章节上下文时，自动检测 `.chroma/` 目录是否存在。如果存在，自动开启语义检索：

```python
# ContextBuilder.build() 中的混合上下文逻辑

# 线性上下文（始终有）
parts = [story_frame, roles, summaries, hooks, ...]

# 语义补充（可选）
if has_vector_store(project_dir):
    semantic_hits = retriever.retrieve_for_chapter(ch_num, query)
    parts.append(semantic_hits.format_for_prompt())

# 总字数不超过 8000
```

**混合策略的优势：**

- 线性摘要保证"最近 5 章发生了什么"（时间相邻性）
- 语义检索补充"很久以前但高度相关的细节"（语义相关性）
- 两者互补，不互相替代

---

## 五、CLI 设计

```bash
# 构建索引
python main.py index --name "无名密探"

# 强制重建（清空旧数据）
python main.py index --name "无名密探" --force
```

---

## 六、实跑验证

**测试：《无名密探》索引 + 检索**

```
索引构建:
  foundations: 6 条
  chapters: 8 条
  hooks: 5 条

测试查询: "破庙 记忆替换"
  命中 1 (0.94): "沈安在破庙醒来，发现自己的记忆又被替换了"
  命中 2 (0.87): "遗忘石是一种可以记录记忆修改的石头"

第 2 章写作中语义检索:
  正确命中破庙/阿沅/刀疤相关段落，辅助 Writer 保持前后一致
```

---

## 七、已知问题

- **test_add_and_query 持久化泄漏**（已修复）：pytest 不清理 ChromaDB 测试目录，导致重复跑时 count 累加。修复：添加 autouse cleanup fixture。
- **模型首次加载慢**：13.7s（470MB 磁盘 IO）。这是 sentence-transformers 的固有限制，后续版本可考虑更轻量的嵌入模型。
