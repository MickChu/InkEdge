# Phase 5 — 后验校验系统

> 版本：0.1（设计稿）
> 日期：2026-05-24
> 状态：设计阶段

---

## 一、问题定义

### 1.1 当前痛点

Writer 写完一章后，没有自动质量检查。以下问题全靠人工复读发现：

- **重复内容**：第 10 章和第 3 章写了几乎相同的情节/对话/描写段落
- **AI 痕迹**：过度使用"突然""竟然""值得注意的是""综上所述"等 AI 高频词汇
- **一致性断裂**：角色眼睛颜色前后矛盾、第 5 章死了的配角第 12 章又出现了
- **伏笔断链**：第 8 章埋的钩子到完本都没回收

### 1.2 为什么不在 Writer 生成时做

Writer 的职责是创作。在创作的同时做质检会让提示词膨胀、降低生成质量。后验校验是独立的"审稿"环节——写完再审，创作和质检解耦。

---

## 二、设计理念

### 2.1 三校验器并行架构

```
Writer 写完新章节
    │
    ├──→ DuplicationChecker     (重复检测)
    ├──→ AIStyleScorer           (AI 痕迹评分)
    └──→ ConsistencyValidator    (一致性校验)
          │
          ▼
    校验报告 → CLI 输出 / 写入文件
    严重问题 → 标记 + 建议重写
    轻微问题 → 提示 + 可选修复
```

### 2.2 核心原则

1. **不阻塞写稿流程**：校验是建议性的，不拒绝保存章节
2. **可配置阈值**：用户能调"多相似算重复"、"多高分算 AI 味"
3. **向量检索驱动重复检测**：利用已有的 ChromaDB 做语义相似度比较
4. **规则 + 统计双引擎**：AI 痕迹用硬规则（关键词黑名单）+ 软统计（句式分布）
5. **CLI 先通，GUI 后跟**：先做 `python main.py check --name "书" --chapter 10`，再在 Streamlit 上做可视化的审稿界面

---

## 三、校验器设计

### 3.1 DuplicationChecker — 重复检测

**原理：**

把新章节分段（每段 200-500 字），用已有的 VectorStore 对各段做语义搜索。如果某段与任意历史章节的余弦相似度超过阈值（默认 0.92），标记为疑似重复。

**数据结构：**

```python
@dataclass
class DuplicateReport:
    new_segment: str              # 新章节中的段落
    matched_segment: str          # 历史中匹配的段落
    similarity: float             # 余弦相似度 (0-1)
    source_chapter: int           # 匹配段落所在章节
    severity: str                 # "high" / "medium" / "low"
```

**算法流程：**

```
1. 将新章节文本按段落边界拆分为 segments[]
2. 对每个 segment:
   a. 在 VectorStore 的 chapters collection 中 search(segment, n=3)
   b. 如果 top-1 的 distance < 阈值:
      → 记录为疑似重复
3. 汇总所有 segment 的结果
4. 去重：连续多段命中同一源章节 → 合并为一条"大面积重复"
```

**阈值建议：**

| 级别 | 相似度 | 处理方式 |
|------|--------|----------|
| 严重 | ≥ 0.95 | 标记重写 |
| 中等 | 0.90–0.95 | 提示用户 |
| 轻微 | 0.85–0.90 | 仅记录 |

### 3.2 AIStyleScorer — AI 痕迹评分

**原理：**

建立两个评估维度：
1. **硬规则（关键词黑名单）**：统计 AI 高频词汇的出现次数
2. **软统计（句式分布）**：分析句长分布、连接词密度、对白比例

**黑名单词汇：**

| 类别 | 示例 |
|------|------|
| 转折偷懒词 | 突然、竟然、原来、不料、谁知 |
| AI 套话 | 值得注意的是、综上所述、不仅…更…、在这个…中 |
| 表情偷懒 | 微微一笑、嘴角上扬、眼中闪过一丝、深吸一口气 |
| 过度连接 | 与此同时、另一方面、紧接着、随即 |

**评分公式：**

```
AI味得分 = 黑名单词密度 × 0.4 + 句长标准差/均值 × 0.2 + 连接词密度 × 0.2 + 描写比例偏离 × 0.2

黑名单词密度 = 命中次数 / 总字数 × 10000  (每万字命中数)
句长标变比 = std(各句字数) / mean(各句字数)  (<0.5 太均匀 → AI味)
连接词密度 = 连接词出现次数 / 总句数
描写比例偏离 = |实际对白比例 - 最佳区间(0.3-0.5)| / 0.5
```

**输出：**

```
AI 痕迹评分: 23/100 (良好)
├─ 黑名单词: 4次  (偏低)
│  └─ "微微一笑" 第12段, "突然" 第3段, "突然" 第8段, "竟然" 第15段
├─ 句长分布: 0.62  (正常)
├─ 连接词密度: 0.08/句 (偏低)
└─ 对白比例: 0.35 (正常)
```

### 3.3 ConsistencyValidator — 一致性校验

**原理：**

利用 foundation 文件和已保存的角色状态作为"真相源"，逐条检查新章节中的关键实体是否一致。

**检查维度：**

| 维度 | 检查内容 | 方式 |
|------|----------|------|
| 角色名 | 主角/重要配角的名字是否与设定一致 | 字符串匹配 |
| 角色状态 | 角色在上一章的状态与新章是否连贯 | 读 character_state |
| 规则遵循 | 是否违反了 book_rules 中的 prohibitions | 语义搜索 + 规则匹配 |
| 伏笔回收 | pending_hooks 中有哪些本章应该回收 | 正则匹配 |
| 时间线 | 章间时间推进是否合理 | 提取时间词比对 |

**数据结构：**

```python
@dataclass
class ConsistencyIssue:
    issue_type: str               # "name" / "state" / "rule" / "timeline"
    description: str              # 人类可读的描述
    source_ref: str               # 引用来源（如 "roles.md § 沈安"）
    chapter_ref: str              # 有问题的章节段落
    severity: str                 # "error" / "warning" / "info"
```

---

## 四、CLI 设计

```bash
# 检查最新一章
python main.py check --name "无名密探"

# 检查指定章节
python main.py check --name "无名密探" --chapter 10

# 批量检查
python main.py check --name "无名密探" --from 1 --to 10

# 只检查重复
python main.py check --name "无名密探" --chapter 10 --mode duplicate

# 只检查 AI 痕迹（输出详细报告）
python main.py check --name "无名密探" --chapter 10 --mode ai --verbose
```

**输出示例：**

```
🔍 后验校验: 无名密探 第10章 (4512字)

📋 重复检测 — ✅ 通过
   未发现显著重复

🤖 AI痕迹评估 — ⚠️ 注意 (32/100)
   ├─ "突然" 出现 5 次（偏高）
   ├─ "微微一笑" 第8段 — 建议替换
   └─ 句长过于均匀 (标变比 0.41) — 建议长短交替

🔗 一致性校验 — ⚠️ 1个问题
   └─ 角色"阿沅"在第5章已刻画疤在右腕，本章第23段写为左腕
```

---

## 五、集成点

### 5.1 Writer 写后自动触发

```python
# main.py cmd_write 末尾追加
if not args.skip_check:
    result = await run_post_write_checks(project_dir, chapter_num, chapter_text)
    print_check_report(result)
```

### 5.2 校验模块目录结构

```
src/validation/
├── __init__.py
├── checker.py              # CheckOrchestrator — 三校验器调度
├── duplication.py          # DuplicationChecker
├── ai_style.py             # AIStyleScorer
├── consistency.py          # ConsistencyValidator
└── report.py               # CheckReport 数据类 + 格式化输出
```

### 5.3 依赖关系

| 校验器 | 依赖 |
|--------|------|
| DuplicationChecker | VectorStore（已有） |
| AIStyleScorer | 无外部依赖（纯规则+统计） |
| ConsistencyValidator | foundation 文件 + character_state + book_rules |

Phase 5 可以在不修改任何已有模块的情况下实现——它只读、不写。

---

## 六、未来改进方向

### 6.1 上下文感知的重复判定（v1.1）

当前是纯语义相似度。未来加入"上下文豁免"——如果两段都提到"破庙"，但分别是第三章的初入破庙和第十章的重返破庙（有情节进展），不应判定为重复。

### 6.2 自动修复建议（v1.2）

对于 AI 痕迹问题，不只是标记，还给出替换建议：
> "微微一笑" → 建议替换为具体的表情描写或动作

### 6.3 章节间连贯性评分（v2.0）

不只是查错，还做整体写作质量评估：
- 章节张力曲线（开头、中段、结尾的情绪强度分布）
- 伏笔密度合理性（太多→乱，太少→平）
- 章节独立性（自己算不算一个完整的小故事弧）

---

## 七、决策记录

- **2026-05-24**：三校验器并行架构确立。DuplicationChecker 复用已有 VectorStore。
- 设计选择：校验不阻塞写稿、可配置阈值、规则+统计双引擎。
