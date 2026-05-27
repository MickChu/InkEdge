# Phase 2 — Architect Agent（架构师）

> 状态：✅ 已完成（2026-05-23）
> 测试：14/14 通过

---

## 一、设计目标

Architect 是小说的"总设计师"。它的职责是在写第一个字之前，产生完整的基础设定方案——故事框架、世界观、角色、规则、伏笔、分卷计划。

---

## 二、设计演进

### 2.1 第一版：Snowflake 雪花法（6步分步生成）

```
Step 1: 核心种子       → 一句话概括 + 主角 + 冲突
Step 2: 角色动态       → 角色关系网 + 驱动力
Step 2.5: 角色状态     → 物品/能力初始状态
Step 3: 世界观构建     → 世界规则 + 铁律
Step 4: 情节架构       → 三幕结构 + 分卷
Step 5: 章节大纲       → 每章一句话摘要
```

**优点**：每步独立验证，可断点续传。
**缺点**：6 次 LLM 调用，步间信息传递有损失，世界观步骤容易公式化（"物理/社会/隐喻"三维框架）。

### 2.2 第二版：Unified Foundation（一次调用输出全部）

来自老板的反馈——"inkOS 对小说世界观的处理比较符合想法"。

**核心变革：**

- **一次 LLM 调用** 产出全部 5 个 SECTION
- **世界观不独立成篇**，而是融入 `story_frame` 的第 3 段——作为故事的有机组成，不是百科全书
- **严格去重**：每个事实只在它的权威位置出现一次

**5 个 SECTION 结构：**

```
=== SECTION: story_frame ===     # 故事框架（4段散文: 主题/冲突/世界观底色/终局）
=== SECTION: volume_map ===     # 分卷地图（散文: 主题/情绪流/钩子/节奏原则）
=== SECTION: roles ===          # 角色卡（一人一卡散文: 标签/反差/小传/弧线/关系）
=== SECTION: book_rules ===     # 硬限制（YAML: 主角约束/类型锁/禁止项）
=== SECTION: pending_hooks ===  # 初始伏笔（前台+后台各5条）
```

### 2.3 Phase 2c 修复的三个问题

1. **配置系统**：API Key 硬编码 → 三级优先级（env > yaml > default）
2. **世界观公式化**：强制"物理/社会/隐喻"三维 → 散文化铁律 + 感官锚
3. **角色名一致性**：后续步骤引用角色名时容易错字 → `extract_character_names()` 提取后注入后续步骤

---

## 三、Architect 内部流程

```
ArchitectAgent.run(context)
  │
  ├─ unified 模式:
  │   ├─ 1. 加载 unified 模板
  │   ├─ 2. 填入参数 (topic/genre/chapters/words/guidance)
  │   ├─ 3. 一次 LLM 调用
  │   ├─ 4. foundation_parser.parse_sections() 解析5段
  │   └─ 5. save_sections() 写入独立文件
  │
  └─ snowflake 模式（备选）:
      ├─ 6步分步执行
      └─ 每步保存 partial_architecture.json（断点续传）
```

**输出文件：**

```
projects/书名/
├── story_frame.md         # 故事框架
├── volume_map.md          # 分卷计划
├── roles.md               # 角色卡
├── book_rules.md          # 硬规则
└── pending_hooks.md       # 初始伏笔
```

---

## 四、提示词模板系统

### 4.1 可插拔模板架构

```python
TemplateRegistry      # 全局注册中心
  ├─ unified          # inkOS 风格（默认）
  └─ snowflake        # 雪花法（备选）

添加新写作方法论:
  1. 在 prompts/ 下新建目录
  2. 每步一个 .py 文件（TemplateStep）
  3. __init__.py 组装 PromptTemplateSet
  4. base_template.py 注册
```

### 4.2 TemplateStep 结构

```python
TemplateStep(
    order=1,
    name="核心种子",
    prompt="你是... {topic} ... {genre} ...",
    required_params=["topic", "genre", "chapters"],
    output_key="core_seed",
)
```

支持浮点排序（如 step 2.5 插在 2 和 3 之间）。

---

## 五、设计原则

### 世界观设计原则

```
❌ 旧方式（公式化）:
  力量体系:
    1. 法力来源: 记忆
    2. 施法代价: 遗忘
    3. 极限: 姓名

✅ 新方式（散文化）:
  这个世界的法力来自于记忆——施法越多，忘得越快。
  最强大的术士，往往连自己的名字都不记得。
```

### 去重原则

- 主角弧线 → 只写在 roles
- 世界铁律 → 只写在 story_frame 段3
- 伏笔 → 只写在 pending_hooks
- 每个事实只在权威位置出现一次

---

## 六、实跑验证

**测试作品**：《无名密探》（悬疑奇幻）

```
模板: unified
字数: 9524 字（5 段总计）
Token: 8192
5/5 SECTION 解析成功

产出质量亮点:
- 世界观是专属于这个故事的（蜕衣术、遗忘石、天听密探体系）
- 8 条初始伏笔，前台+后台双层覆盖
- 角色卡包含反差细节（沈安外冷内热、阿沅刀疤来历）
```
