# Phase 6 — 角色状态追踪系统

> 版本：0.1（设计稿）
> 日期：2026-05-24
> 状态：设计阶段

---

## 一、问题定义

### 1.1 当前痛点

写 60 章的长篇小说时，Writer 只知道"这一章的上下文"——最近 5 章摘要 + foundation 设定。但对于跨章漫长时间线中的角色变化，存在严重的信息衰减：

- **物品追踪断裂**：第 3 章主角捡了一把匕首，第 23 章又"从怀里掏出匕首"，但第 15 章匕首明明掉进了悬崖
- **能力成长断档**：第 10 章主角学会基础剑法，第 40 章突然使出"破空十三剑"——中间 30 章没有任何学习过程的记录
- **关系网静滞**：角色 A 和角色 B 在第 8 章反目成仇，但 Writer 在第 25 章仍然把他们当作盟友写

### 1.2 为什么 Chapter Summaries 不够

章节摘要是**叙事导向**的（"主角去了破庙，发现了秘密"），它是给后续章节提供情节衔接的。但角色状态是**实体导向**的——你需要精确知道：

- 主角当前持有的物品列表
- 主角当前的能力/功法等级
- 主角与每个角色的关系状态和最近一次互动

这些是结构化的、可查询的数据，不适合埋在散文摘要里。

---

## 二、设计理念

### 2.1 增量状态更新

每写完一章，StateManager 执行以下流程：

```
新章节正文
    │
    ├──→ InventoryTracker  ──→ 更新物品清单（获得/使用/丢失）
    ├──→ AbilityTracker    ──→ 更新能力状态（学习/升级/遗忘）
    └──→ RelationshipTracker ──→ 更新关系网（亲近/疏远/敌对）
          │
          ▼
    写入 character_state.json
    写入 character_state.md（人类可读版本）
```

### 2.2 核心原则

1. **增量不重算**：每章只提取本章的变化，追加到已有状态上
2. **双格式输出**：`.json` 给程序读（精确查询），`.md` 给人看（方便调试）
3. **可回滚**：每次更新保存快照，出错可回退到任意章节的状态
4. **与 Writer 上下文融合**：写下一章时，当前角色状态自动注入 ContextBuilder

### 2.3 数据结构（character_state.json）

```json
{
  "project": "无名密探",
  "last_chapter": 10,
  "updated_at": "2026-05-24T06:00:00",
  
  "characters": {
    "沈安": {
      "role": "protagonist",
      "inventory": [
        {
          "item": "遗忘石",
          "quantity": 1,
          "acquired_chapter": 3,
          "last_used_chapter": 7,
          "status": "持有"
        },
        {
          "item": "天听阁令牌",
          "quantity": 1,
          "acquired_chapter": 5,
          "status": "持有"
        }
      ],
      "abilities": [
        {
          "name": "蜕衣术",
          "level": "玄阶上品",
          "learned_chapter": 1,
          "last_upgraded_chapter": 8,
          "mastery": "熟练"
        }
      ],
      "relationships": {
        "阿沅": {
          "status": "同伴",
          "trust": 85,
          "last_interaction_chapter": 10,
          "last_interaction_summary": "一起逃离天听阁地下废墟"
        },
        "赵肃": {
          "status": "敌对",
          "trust": -20,
          "last_interaction_chapter": 9,
          "last_interaction_summary": "在西门对峙，赵肃拒绝交出钥匙"
        }
      },
      "physical_state": "左臂轻伤（第10章获得）",
      "location": "天听阁地下废墟出口"
    }
  },
  
  "snapshots": {
    "5": "state_snapshot_05.json",
    "10": "state_snapshot_10.json"
  }
}
```

---

## 三、追踪器设计

### 3.1 InventoryTracker — 物品追踪

**提取逻辑：**

用 LLM 解析本章正文，提取所有物品变化事件：

```
输入：第10章正文
输出：
  + 获得：青铜钥匙（从天听阁废墟找到）
  - 使用：解毒丹×1（给阿沅服用）
  - 丢失：匕首（坠入地缝）
```

**提示词设计：**

```
你是物品追踪器。阅读以下章节正文，提取所有物品变化：

## 现有物品
{current_inventory}

## 新章节
{chapter_text}

请以严格 JSON 格式输出物品变化：
{
  "acquired": [{"item": "名称", "detail": "来源"}],
  "used": [{"item": "名称", "detail": "用途"}],
  "lost": [{"item": "名称", "detail": "去向"}]
}

规则：
- 只输出本章新发生的变化
- 消耗品（丹药、食物）归为 used 并标记数量变化
- 如果物品短暂离手但主角又拿回来，不算 lost
- 如果本章没有某个类别的变化，对应数组为空
```

### 3.2 AbilityTracker — 能力追踪

**提取逻辑：**

检测本章中的能力变化——学习、升级、领悟、突破、使用后遗症等。

```
输入：第10章正文
输出：
  + 升级：蜕衣术 → 地阶下品（在废墟中领悟第三重）
  + 新学：废墟感知（能在黑暗中感知周围 10 步）
```

**提示词设计关键点：**

- 不只有功法，还包括：技能、知识、天赋觉醒、体术
- 区分"本章使用了已有能力"（不记录）和"能力本身变化了"（记录）
- 如果用了但代价是永久失去部分能力→记录为"削弱"

### 3.3 RelationshipTracker — 关系追踪

**提取逻辑：**

这是最复杂但最重要的追踪器。需要追踪：

- 角色间的情感方向变化（正向/负向）
- 关系性质变化（陌生人→同伴→师徒→恋人→仇敌）
- 重大互动事件（救命、背叛、托付、诀别）
- 信任度的量化估算

**输出格式：**

```json
{
  "relationship_changes": [
    {
      "character": "阿沅",
      "change_type": "信任加深",
      "event": "沈安在废墟中救了阿沅",
      "trust_delta": 15,
      "new_status": "同伴（信任加深）"
    }
  ]
}
```

**信任度模型：**

```
信任度区间: -100(死敌) … 0(陌生) … 100(至交)

变化幅度参考:
  +5~10:  日常互动、闲聊
  +15~25: 帮助、共患难
  +30~50: 救命、托付秘密
  -5~10:  小摩擦、误解
  -15~25: 背叛、伤害
  -30~50: 杀亲、灭门、不可逆的打击
```

---

## 四、集成点

### 4.1 写后自动触发

```python
# main.py cmd_write 末尾
state = StateManager(project_dir)
state.post_write(chapter_num, chapter_text)        # Phase 3 已有的摘要
state.update_character_state(chapter_num, chapter_text)  # Phase 6 新增
```

### 4.2 写前注入上下文

```python
# ContextBuilder.build() 中
character_state = read_file("character_state.md")
context.current_state = format_character_state_for_context(character_state)
```

ContextBuilder 已有关键字段 `current_state` 和预算 `500 字`，直接把结构化状态压缩成摘要文本塞进去即可。

### 4.3 目录结构

```
src/state/
├── __init__.py
├── manager.py              # StateManager（Phase 3 已有，需扩展）
├── inventory_tracker.py    # InventoryTracker
├── ability_tracker.py      # AbilityTracker
└── relationship_tracker.py # RelationshipTracker
```

### 4.4 CLI 命令

```bash
# 查看角色状态
python main.py state --name "无名密探"

# 输出示例：
# 📋 角色状态: 无名密探（更新至第10章）
#
# ⚔️ 沈安
#   物品: 遗忘石, 天听阁令牌, 青铜钥匙
#   能力: 蜕衣术(地阶下品·熟练), 废墟感知
#   关系:
#     阿沅 — 同伴 (信任:85) · 最近: 第10章 一起逃离废墟
#     赵肃 — 敌对 (信任:-20) · 最近: 第9章 西门对峙
#   位置: 天听阁地下废墟出口
#   状态: 左臂轻伤

# 查看历史快照
python main.py state --name "无名密探" --snapshot 5
```

---

## 五、与 Phase 5 的协作

Phase 5 的 ConsistencyValidator 会读取 `character_state.json` 做一致性校验：

```
角色"阿沅"在第5章已刻画疤在右腕 → character_state.json 记录为右腕
第10章正文中写为左腕 → ConsistencyValidator 检测到矛盾 → 标记
```

Phase 5 是质检层，Phase 6 是数据层。二者配合形成闭环。

---

## 六、未来改进方向

### 6.1 角色状态可视化（v1.1）

在 GUI 中展示角色关系网络图——节点是角色，连线是关系类型（盟友/敌人/师徒），颜色深浅表示信任度。

### 6.2 关系网的蝴蝶效应预警（v1.2）

当 Writer 准备写某个角色的重大行为时，系统自动分析：这个行为会影响哪些其他角色？关系网会发生什么连锁变化？

> "你计划让沈安背叛阿沅。影响范围分析：阿沅（信任归零）、赵肃（可能趁机拉拢阿沅）、天听阁势力格局改变。建议在第X章铺垫。"

### 6.3 能力树的叙事约束（v2.0）

不只是记录能力，而是约束能力的"合法使用场景"：
- "蜕衣术"只能在记忆相关场景使用
- "废墟感知"需要黑暗环境
- 如果 Writer 在阳光下用了"废墟感知"，ConsistencyValidator 标记

---

## 七、决策记录

- **2026-05-24**：三追踪器设计确立（物品/能力/关系）。每章增量更新，不复算全章。
- 设计选择：LLM 辅助提取（物品变化、能力变化、关系变化）+ JSON 结构化存储 + 人读 Markdown 副本。
- 数据格式选择：JSON 主存储便于程序查询，Markdown 副本便于人工审查和调试。
