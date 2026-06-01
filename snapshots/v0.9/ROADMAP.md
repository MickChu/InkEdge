# InkEdge 开发路线图

> 最后更新：2026-05-25 · 当前版本：**v0.8**

---

## 版本概览

| 版本 | 状态 | Phases | 说明 |
|:----:|:----:|--------|------|
| v0.8 | **当前** | 1~9, 11 | 完整闭环可用（write → check → settle → index） |
| v0.9 | 下一版 | +10 | 加入环境诊断（doctor） |
| v1.0 | 目标 | +12 | 模块协议化，可扩展架构成熟 |

---

## ✅ 已交付（v0.8）

### Phase 1 — 项目骨架
- **位置**: `src/core/`
- **内容**: Agent 基类（`BaseAgent` / `AgentContext`）、管线编排器（`Orchestrator`）、LLM 客户端、配置系统、上下文预算管理
- **设计文档**: `doc/phase1_skeleton.md`

### Phase 2 — Architect 建书
- **位置**: `src/agents/architect.py`
- **内容**: 统一建书流程（unified foundation），生成 `story_frame.md` / `roles.md` / `book_rules.md` / `volume_map.md` 等核心设定
- **设计文档**: `doc/phase2_architect.md`

### Phase 3 — Writer 写稿
- **位置**: `src/agents/writer.py`
- **内容**: ContextBuilder 组装上下文 + LLM 生成章节正文，支持用户 guidance 引导
- **设计文档**: `doc/phase3_writer.md`

### Phase 3.5 — Style 风格系统
- **位置**: `src/governance/style/`
- **内容**: 六步风格推导流程，生成 8 维风格指南，写稿时自动注入
- **设计文档**: `doc/phase35_style.md`

### Phase 4 — 向量检索
- **位置**: `src/retrieval/`
- **内容**: ChromaDB + sentence-transformers 本地嵌入、语义检索（写稿时自动检索 Top-K 相关内容）、全量索引
- **设计文档**: `doc/phase4_vectorstore.md`

### Phase 5 — 后验校验
- **位置**: `src/validation/`
- **内容**: 重复检测（语义相似度） + AI 痕迹评分 + 一致性校验（book_rules 规则约束）
- **设计文档**: `doc/phase5_post_check.md`

### Phase 6 — 状态追踪
- **位置**: `src/state/`
- **内容**: 角色物品/能力/关系图增量更新、StateManager 自动追章
- **设计文档**: `doc/phase6_state_tracking.md`

### Phase 7 — GUI
- **位置**: `studio.py` + `pages/`
- **内容**: Streamlit 7 页面 Web 界面（建书 / 写稿 / 风格 / 索引 / 校验 / 状态 / 市场雷达）
- **设计文档**: `doc/phase7_gui.md`

### Phase 8 — 类型知识注入
- **位置**: `src/genre_knowledge/`
- **内容**: 可插拔类型知识系统，6 种类型（武侠/奇幻/科幻/历史/悬疑/都市），写稿时自动注入对应类型的命名规范、等级体系、世界观规则
- **设计文档**: `doc/phase8_genre_knowledge.md`

### Phase 9 — 市场雷达
- **位置**: `src/radar/`
- **内容**: 番茄小说/起点排行榜抓取分析、品类趋势识别、分类归并、开书建议
- **设计文档**: `doc/phase9_market_radar.md`

### Phase 11 — 结算系统
- **位置**: `src/settlement/`
- **内容**: Observer（事实提取） + 3 并行 Settler（World / Plot / Character），每章写完后自动结算状态
- **设计文档**: `doc/phase10_doctor.md` ← 实际在 phase10 文件里描述了 settlement 的架构，Phase 编号在开发过程中有过调整
- **设计文档（补充）**: `doc/phase12_protocolization.md` 附录

---

## ⏳ 开发中 / 下一版（v0.9 → v1.0）

### Phase 10 — 环境诊断（Doctor）

> 优先级：高 | 预计工时：1 天 | 设计文档：`doc/phase10_doctor.md`

**目标**: 一条命令 `python main.py doctor` 跑完所有环境检查，输出可读的 pass/fail 报告。

**四层检查**:
| 层级 | 检查项 | 严重性 |
|------|--------|:--:|
| 环境层 | Python 版本 ≥ 3.10、核心 pip 包、嵌入模型缓存、ChromaDB 读写 | error |
| 配置层 | config.yaml 存在/格式、base_url 可解析、model_name 非空 | error |
| 连接层 | API 连通性（发测试请求 → OK）、模型可用性、响应延迟、回退模型 | error/warning |
| 项目层 | 项目文件完整性、ChromaDB 索引健康状态 | warning |

**CLI 接口**:
```bash
python main.py doctor                  # 全检
python main.py doctor --api-only       # 仅 API 连通性
python main.py doctor --project "xxx"  # 特定项目
python main.py doctor --json           # JSON 输出（供脚本）
python main.py doctor --fix            # 自动修复简单问题
```

**新增文件** (7 个):
```
src/doctor/
├── __init__.py
├── checker.py              # DoctorOrchestrator
├── checks_env.py           # Python / pip / 模型缓存 / ChromaDB
├── checks_config.py        # config.yaml / base_url / model
├── checks_api.py           # API 连通 / 模型可用 / 回退模型
├── checks_project.py       # 项目完整性 / 索引状态
└── report.py               # DoctorReport + 格式化输出
```

---

### Phase 12 — 模块协议化

> 优先级：中 | 预计工时：2-3 天 | 设计文档：`doc/phase12_protocolization.md`

**目标**: 为 3 个高频扩展模块定义标准协议（ABC），新增扩展点不需改动核心代码。

**三个协议**:

| 协议 | 位置 | 改造范围 | 扩展性 |
|------|------|---------|:--:|
| `ContextSource` | `src/utils/context_source.py` | ContextBuilder 硬编码的 10 个来源 → 可插拔 list | 高（每个新功能都可能需注入上下文） |
| `CheckProtocol` | `src/validation/check_protocol.py` | 3 个硬编码 checker → 可注册 list | 中（新增校验维度时零侵入） |
| `StateDimension` | `src/state/state_dimension.py` | 3 个独立 dataclass → 统一 StateDimension 协议 | 低（扩展频率低，但统一后整洁） |

**实施顺序**: ContextSource → CheckProtocol → StateDimension

**预计新增测试**: 30 个用例

---

## 💡 远期方向（v1.1+，待定）

以下方向已记录但未纳入正式 Phase，视实际需求决定优先级：

| 方向 | 来源 | 说明 |
|------|------|------|
| 启动时自动 doctor | Phase 10 §7.1 | main.py 启动时快速自检，有问题提示 |
| 定时健康检查 | Phase 10 §7.2 | cron job 每日跑 doctor → 写日志 |
| 性能基准 | Phase 10 §7.3 | LLM 速度 / 嵌入速度 / ChromaDB 延迟基线 + 回归 |
| Doctor GUI 面板 | Phase 10 §7.4 | Streamlit 可视化诊断面板 |
| 同步脚本 | `sync_rules.md` | `sync_to_open_source.py` 自动处理 InkEdge → InkEdge_git 降级同步 |
| 测试修复 | — | 修复 `return True` → `assert` 的 17 个 pytest 警告 |
| 项目清理 | — | 移除遗留的 `.novelforge_checkpoint.json`、旧命名引用 |

---

## 参考

### GitHub 竞品分析
- [RhythmicWave/NovelForge](https://github.com/RhythmicWave/NovelForge): 卡片模型 + 记忆层 + 审核系统
- 分析文档: `knowledge/github_novelforge_reference.md`（备查，不纳入 Phase）

### 融合来源
- [inkOS](https://github.com/actalk/inkos) — 结算系统、市场雷达、环境诊断、角色状态追踪的设计参考
- [AI_NovelGenerator](https://github.com/fathah/AI_NovelGenerator) — 多阶段流水线、向量检索、雪花法、状态追踪的思想来源

---

## 变更记录

| 日期 | 版本 | 变更 |
|------|:----:|------|
| 2026-05-25 | v0.8 | 创建路线图，确认闭环验证通过，整理待开发计划 |
| 2026-05-24 | v0.8 | 项目改名 NovelForge → InkEdge，端到端验证 125/125 |
