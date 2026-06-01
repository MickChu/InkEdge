# Phase 8 — 类型知识注入系统

> 版本：0.1（设计稿）
> 日期：2026-05-24
> 状态：设计阶段

---

## 一、问题定义

### 1.1 当前痛点

InkEdge 的 Architect 和 Writer 是"通用型"Agent——它们理解"写小说"的流程，但对自己所写的类型缺乏深度知识。

**一个具体的例子：**

用户输入 `--genre 武侠`，Architect 生成的统一基础设定（unified foundation）产出了：

```
角色：沈安
身份：前天听阁密探统领
```

它知道"密探"和"统领"对武侠是合理的词汇，但它**不知道**可以更进一步：

```
角色：沈安
表字：守拙
身份：前天听阁密探统领，从三品衔
功法：蜕衣术（玄阶上品），可剥离七日记忆
```

差距不在于词汇量，而在于**类型知识的结构化缺失**：
- 武侠体系里角色应该有"表字"
- 官职应该带品阶
- 功法应该有品级命名惯例（天地玄黄 / A B C D）
- 门派应该有辈分字、门规、领地

### 1.2 为什么 Style System（Phase 3.5）不够

| | Phase 3.5 Style System | Phase 8 知识注入 |
|---|---|---|
| 解决什么 | "写出来读起来像金庸"（腔调） | "世界观构件符合该类型的常识"（骨头） |
| 输入 | 作家文本片段 | 类型领域知识 |
| 作用端 | Writer 输出端 | Architect 建书端 + Writer 上下文 |
| 本质 | 模仿某个人的叙事习惯 | 理解某个类型的设定体系 |

两者互补不重叠。风格模仿腔调，知识注入骨架。

---

## 二、设计理念

### 2.1 核心原则

**"不是教 AI 学一个新类型的所有知识，而是告诉它这个类型有什么特殊的命名惯例和组织结构。"**

模型本身已经有大量类型知识。缺少的不是知识本身，而是**在提示词里结构化地提醒它"该类型的设定应该长什么样"**。

因此设计原则：

1. **注入而非训练**：不微调模型，只在提示词中注入类型知识框架
2. **结构而非词典**：不是给一堆术语列表，而是给一个"设定骨架"——该类型里什么东西有名字、什么东西有等级、什么东西有规则
3. **可插拔**：新类型只需在 `genre_knowledge/` 下加一个 `.py` 文件
4. **对用户透明**：用户只写 `--genre 科幻`，不需要知道背后的知识文件
5. **不污染通用路径**：如果没找到对应知识文件，不报错，降级为当前行为

### 2.2 与现有系统的关系

```
                 InkEdge 系统架构（Phase 8 注入点）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  main.py (CLI)
    │  --genre 武侠
    │
    ▼
  ArchitectAgent.run()
    │  ① 加载类型知识 → 注入 unified foundation prompt
    │     "你正在写一本武侠小说。该类型的设定惯例：……"
    │  ② 知识也写入 AgentContext.extra，传递给下游
    ▼
  WriterAgent.run()
    │  ③ 从 ContextBuilder 获取类型知识段落
    │  ④ Writer 系统提示词增加 genre_conventions 段落
    ▼
  ContextBuilder.build()
    │  ⑤ 加载类型知识，写入 ChapterContext
    ▼
  提示词 → LLM
```

---

## 三、实现方案

### 3.1 目录结构

```
InkEdge/
├── src/
│   └── genre_knowledge/          ← 新增
│       ├── __init__.py            # KnowledgeLoader, get_genre_knowledge()
│       ├── base.py                # GenreKnowledge 数据类
│       ├── registry.py            # 知识注册中心
│       └── genres/
│           ├── __init__.py
│           ├── wuxia.py           # 武侠 / 仙侠 / 古风
│           ├── scifi.py           # 科幻
│           ├── urban.py           # 都市 / 现实
│           ├── mystery.py         # 悬疑 / 推理
│           ├── fantasy.py         # 西方奇幻
│           └── historical.py      # 历史
│
└── prompts/
    └── genre_knowledge/           ← 各类型的提示词注入模板（Markdown）
        ├── wuxia_injection.md
        ├── scifi_injection.md
        └── ...
```

### 3.2 核心数据结构

```python
# src/genre_knowledge/base.py

@dataclass  
class GenreKnowledge:
    """一个类型的领域知识"""
    genre: str                          # 唯一标识 (wuxia/scifi/urban/...)
    display_name: str                   # 显示名 (武侠/科幻/都市/...)
    
    # 提示词注入文本（在建书/写稿提示词中插入的段落）
    injection_text: str                 # 完整注入文本
    
    # 细粒度组件（可选，方便未来模块化）
    naming_conventions: str = ""        # 命名惯例
    hierarchy_systems: str = ""         # 等级/组织体系
    world_rules: str = ""              # 世界观规则模板
    character_traits: str = ""         # 角色特征惯例
    plot_patterns: str = ""            # 叙事模式惯例
    
    # 元信息
    version: str = "1.0"
    description: str = ""
```

### 3.3 知识加载器

```python
# src/genre_knowledge/__init__.py

class KnowledgeLoader:
    """类型知识加载器"""
    
    def __init__(self):
        self._cache: Dict[str, GenreKnowledge] = {}
        self._load_builtin()
    
    def get(self, genre: str) -> Optional[GenreKnowledge]:
        """获取指定类型的知识。无匹配返回 None，调用方降级。"""
        return self._cache.get(genre.lower())
    
    def inject_to_prompt(self, genre: str, base_prompt: str) -> str:
        """向提示词中注入类型知识"""
        knowledge = self.get(genre)
        if not knowledge:
            return base_prompt
        return base_prompt + "\n\n## 类型知识\n" + knowledge.injection_text
    
    def _load_builtin(self):
        """从 genres/ 目录加载所有内置类型知识"""
        ...
```

### 3.4 类型知识文件示例

```python
# src/genre_knowledge/genres/wuxia.py

WUXIA_KNOWLEDGE = GenreKnowledge(
    genre="wuxia",
    display_name="武侠",
    injection_text="""### 武侠小说设定惯例

**命名体系：**
- 角色应有姓名 + 表字（如"沈安，字守拙"），字号与人物性格/命运相关
- 门派/帮派应有：全称、简称、地理位置、门规（1-3条）、辈分字
- 功法命名格式：[描述词] + [核心意象] + 诀/术/功/法（如"蜕衣术""九阳神功"）

**等级体系：**
- 功法品阶：天地玄黄四阶（或甲乙丙丁），每阶分上中下三品
- 武学境界：外功→内功→化境（至少三层递进）
- 官职/宗门职务：需带阶衔（如"从三品带刀侍卫""天听阁内门执事"）

**世界观规则：**
- 力量体系的代价：每种功法/能力须有代价或限制
- 江湖规矩：正道魔道的行为边界、不杀之约、武林大会等
- 历史锚点：如果是历史武侠，皇帝年号、重大历史事件需准确

**角色塑造：**
- 主角应有"入世理由"（为何闯荡江湖？）和"退隐代价"（为何不能退？）
- 每个主要对手有完整动机，不是纯粹的恶人
- 师徒/同门/仇敌关系网是武侠的核心戏剧张力

**禁止项：**
- 避免"今穿古"的语言穿越感（除非是穿越文）
- 避免现代价值观强行套用古代社会
- 避免功法战力体系无限制膨胀
""",
    naming_conventions="...",
    hierarchy_systems="...",
    version="1.0",
    description="中国传统武侠、仙侠类型的世界观设定惯例",
)
```

### 3.5 集成点

#### 3.5.1 ArchitectAgent 集成

在 `ArchitectAgent.run()` 中，加载类型知识并注入到 foundation prompt：

```python
# 关键改动：在构建 prompt 参数时注入类型知识
genre_knowledge = self._get_genre_knowledge(context)
# 将知识文本追加到 user_guidance 或作为独立参数注入
```

改动量：约 10 行。

#### 3.5.2 ContextBuilder 集成

在 `ChapterContext` 中新增 `genre_knowledge` 字段，`build_prompt_context()` 中追加：

```python
# ChapterContext 新增
genre_knowledge: str = ""

# build_prompt_context() 中
if self.genre_knowledge:
    parts.append(f"## 类型写作惯例\n{self.genre_knowledge}")
```

改动量：约 15 行。

#### 3.5.3 CLI 集成

`main.py` 已有 `--genre` 参数，无需改 CLI。只需在内部路由时将 genre 值传给 KnowledgeLoader。

#### 3.5.4 Writer 系统提示词

在 `WRITER_SYSTEM_PROMPT` 末尾追加动态段落。

### 3.6 实现步骤（MVP）

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| Step 1 | 创建 `genre_knowledge/` 模块骨架（base.py + loader） | 小 |
| Step 2 | 编写 2-3 个类型知识文件（wuxia/scifi/urban） | 中 |
| Step 3 | ArchitectAgent 集成（foundation prompt 注入） | 小 |
| Step 4 | ContextBuilder 集成（章节上下文注入） | 小 |
| Step 5 | 单元测试 + 实跑验证 | 中 |

---

## 四、未来改进方向

### 4.1 细粒度知识注入（v1.1）

当前设计是一次性注入全部类型知识。未来可按 Agent 职责拆分：

```
Architect 需要:   naming_conventions + hierarchy_systems + world_rules
Writer 需要:      character_traits + plot_patterns + dialogue_conventions
Reviewer 需要:    plot_patterns（用于一致性检查）
```

### 4.2 用户自定义类型（v1.2）

允许用户在项目目录下放置自定义 `genre_knowledge.yaml`：

```yaml
# projects/我的小说/genre_knowledge.yaml
genre: 赛博武侠
injection_text: |
  这个世界的武学基于神经植入体……
  门派是大型企业的武装部门……
```

优先级：项目级 > 内置。

### 4.3 知识累积学习（v2.0）

观察用户重复手动写入 guidance 的内容，自动提取为类型知识建议：

> "你在武侠项目中 80% 都写了'功法要有明确品阶'，是否加入你的武侠知识库？"

### 4.4 跨类型混合（v2.1）

支持多标签叠加。如 `--genre 武侠+科幻` → 同时加载两种知识，做智能融合：

```
武侠的功法品阶 + 科幻的技术合理性 → "量子内功"
武侠的江湖规矩 + 科幻的社会结构 → "星际宗门"
```

### 4.5 GUI 知识编辑器（v3.0）

Streamlit GUI 中提供可视化的类型知识编辑器——用户可以查看、修改、创建自己的类型知识模板。

---

## 五、与当前完成的 Phase 的关系

```
Phase 1-4  (已完成)   核心生成链路
Phase 3.5  (已完成)   风格控制 → 解决腔调
Phase 4    (已完成)   语义检索 → 解决记忆
Phase 5    (未做)     后验校验 → 解决质量
Phase 6    (未做)     角色追踪 → 解决一致性
Phase 7    (未做)     GUI     → 解决界面
Phase 8    (本方案)   类型知识 → 解决骨头
```

Phase 3.5 + Phase 8 共同决定"写得像不像"：前者管腔调，后者管骨架。

---

## 六、决策记录

- **2026-05-24**：Phase 8 原名"中文古风适配"，老板指出古风只覆盖一个类型，改为通用的**类型知识注入系统**
- 设计原则确立：注入而非训练、结构而非词典、可插拔、对用户透明
- 架构选择：知识文件用 `.py` 而非 `.yaml`，因为需要 Python 对象的类型安全，且未来可能包含后处理逻辑
