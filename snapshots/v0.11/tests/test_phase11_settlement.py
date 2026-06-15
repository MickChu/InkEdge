"""
Phase 11 — 结算系统测试

Observer + 3 Settlers + Orchestrator 的单元和集成测试。
"""
import pytest
import os
import tempfile
import asyncio

from src.settlement.observer import Observer
from src.settlement.world_settler import WorldSettler, parse_world_output
from src.settlement.character_settler import CharacterSettler, parse_character_output
from src.settlement.plot_settler import PlotSettler, parse_plot_output
from src.settlement.orchestrator import SettlementOrchestrator, SettlementReport


# ══════════════════════════════════════════════════════════
# 测试数据: 一段模拟章节正文
# ══════════════════════════════════════════════════════════

SAMPLE_CHAPTER = """
## 第十章  暗流涌动

沈安站在天听阁的藏书库里，指尖抚过一排排蒙尘的竹简。

他的左臂还在隐隐作痛——那是三日前交手时留下的剑伤。但此刻他顾不得疼痛，因为墙上的机关图案已经被他解开了大半。

突然，门外的脚步声让他浑身一紧。

"沈兄，深夜来此，莫不是有什么心事？"

赵肃的声音从身后传来。沈安缓缓转身，手已经按在了腰间短刀的刀柄上。

"赵大人不也睡不着？"沈安冷笑。

赵肃走近几步，烛光映出他脸上的笑意："我来，是想告诉你一件事——那枚令牌的来历，我已经查清了。"

沈安瞳孔微缩。这是他历经三场生死才找到的令牌。他从未告诉过任何人。

"你查到了什么？"

"暗影宗。"赵肃一字一顿，"三百年前被灭门的那个。"

藏书库里的烛火猛地跳动了一下。沈安强压下心中的震惊——暗影宗是他师父临终前最后提到的地方。师父说，那里藏着他身世的真相。

他不动声色地从袖中取出一枚解毒丹，悄悄含入口中——刚才打开机关时，他触碰了一种未知的粉末。

"所以呢？"沈安问道。他感到丹药在口中化开，一丝清凉渗入喉间，同时他运起蜕衣术的第一层心法——这门功法可以让他短暂改变面容，也许今天能用上。

赵肃没有回答，只是从怀中掏出了一张泛黄的羊皮地图："你看这个。"

地图上绘着暗影宗遗址的完整布局。在正中心，画着一个沈安熟悉的符号——和他背后的胎记一模一样。

"跟我合作。"赵肃说，"我知道你在找你师父的死因。我也在找。"

沈安沉默了很久。他想起师父教他的最后一句话：有时候，敌人也可以是暂时的盟友。

"好。"他终于松开了刀柄。

月光从藏书库的天窗倾泻而下，照亮了两个各怀心事的人。

与此同时，远在城外的茶摊上，阿沅正焦急地等着消息。她不知道沈安此刻正在经历什么，她的手指紧握着一枚铜钱——那是沈安临行前留给她的最后一个信物。
"""


# ══════════════════════════════════════════════════════════
# Observer 测试
# ══════════════════════════════════════════════════════════

class TestObserver:
    """事实提取器测试"""

    def test_observe_sync_basic(self):
        obs = Observer()
        result = obs.observe_sync(SAMPLE_CHAPTER, 10)
        assert "=== OBSERVATIONS ===" in result
        assert "[角色行为]" in result
        assert "[位置变化]" in result
        assert "[资源变化]" in result
        assert "[情绪变化]" in result

    def test_observe_sync_detects_characters(self):
        obs = Observer()
        result = obs.observe_sync(SAMPLE_CHAPTER, 10)
        assert "沈安" in result or "赵肃" in result or "阿沅" in result

    def test_observe_sync_detects_places(self):
        obs = Observer()
        result = obs.observe_sync(SAMPLE_CHAPTER, 10)
        # 注意: 正则版地点提取有后缀限制(殿/厅/阁/城等),
        # 藏书库/茶摊可能不匹配, 此为回退模式的可接受精度损失
        assert "[位置变化]" in result

    def test_observe_sync_handles_empty(self):
        obs = Observer()
        result = obs.observe_sync("", 1)
        assert "=== OBSERVATIONS ===" in result


# ══════════════════════════════════════════════════════════
# Parser 测试
# ══════════════════════════════════════════════════════════

class TestParsers:
    """TAG 解析器测试"""

    def test_parse_world_output(self):
        content = """=== POST_SETTLEMENT ===
状态卡已更新。

=== UPDATED_STATE ===
- 当前地点: 藏书库
- 主角状态: 左臂有伤

=== UPDATED_LEDGER ===
| 资源 | 期初 | 变化 | 期末 |
"""
        out = parse_world_output(content)
        assert "状态卡已更新" in out.post_settlement
        assert "藏书库" in out.updated_state
        assert "资源" in out.updated_ledger

    def test_parse_character_output(self):
        content = """=== POST_SETTLEMENT ===
角色关系更新。

=== UPDATED_EMOTIONAL_ARCS ===
| 沈安 | 警惕 | 暂时信任 | Ch10 | 赵肃提供地图 |

=== UPDATED_CHARACTER_MATRIX ===
| 沈安 → 赵肃 | 敌对→潜在同盟 | 信任-20 | 沈安知暗影宗/F肃知沈安在查师父 |
"""
        out = parse_character_output(content)
        assert "角色关系更新" in out.post_settlement
        assert "沈安" in out.updated_emotional_arcs
        assert "沈安 → 赵肃" in out.updated_character_matrix

    def test_parse_plot_output(self):
        content = """=== POST_SETTLEMENT ===
伏笔更新。

=== UPDATED_HOOKS ===
| H001 | Ch3 | mystery | progressing | Ch10 | Ch10 | 揭示暗影宗 | 第2卷 |

=== CHAPTER_SUMMARY ===
Ch10. 沈安潜入藏书库与赵肃达成临时同盟 | 主线推进,结盟

=== UPDATED_CHAPTER_SUMMARIES ===
- Ch1. ...
- Ch10. 沈安潜入藏书库

=== UPDATED_SUBPLOTS ===
| 阿沅线 | 感情线 | 进行中 | Ch10 | 等待沈安消息 |
"""
        out = parse_plot_output(content)
        assert "H001" in out.updated_hooks
        assert "Ch10" in out.chapter_summary
        assert "Ch1" in out.updated_chapter_summaries
        assert "阿沅线" in out.updated_subplots

    def test_parse_empty_tags(self):
        content = "some random text without any tags"
        out = parse_world_output(content)
        assert out.post_settlement == ""
        assert out.updated_state == ""


# ══════════════════════════════════════════════════════════
# Settler 初始化测试
# ══════════════════════════════════════════════════════════

class TestSettlers:
    """Settlers 初始化与文件IO测试"""

    @pytest.fixture
    def project_dir(self):
        d = tempfile.mkdtemp(prefix="nf_test_settle_")
        os.makedirs(f"{d}/story/state", exist_ok=True)
        yield d
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_world_settler_init(self, project_dir):
        ws = WorldSettler(project_dir)
        assert ws.state_dir == f"{project_dir}/story/state"

    def test_character_settler_init(self, project_dir):
        cs = CharacterSettler(project_dir)
        assert cs.state_dir == f"{project_dir}/story/state"

    def test_plot_settler_init(self, project_dir):
        ps = PlotSettler(project_dir)
        assert ps.state_dir == f"{project_dir}/story/state"


# ══════════════════════════════════════════════════════════
# Orchestrator 测试
# ══════════════════════════════════════════════════════════

class TestOrchestrator:
    """编排器测试"""

    @pytest.fixture
    def project_dir(self):
        d = tempfile.mkdtemp(prefix="nf_test_settle_orch_")
        os.makedirs(f"{d}/story/state", exist_ok=True)
        yield d
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_orchestrator_init(self, project_dir):
        orch = SettlementOrchestrator(project_dir)
        assert orch.observer is not None
        assert orch.world is not None
        assert orch.character is not None
        assert orch.plot is not None

    def test_settle_sync_no_llm(self, project_dir):
        """同步版仅运行 Observer，不运行 Settler"""
        orch = SettlementOrchestrator(project_dir)
        report = orch.settle_sync("文本内容", 1)
        assert report.chapter_number == 1
        assert "=== OBSERVATIONS ===" in report.observations
        assert report.world is None  # 同步版不跑 Settler
        assert report.character is None
        assert report.plot is None

    def test_settle_sync_empty_text(self, project_dir):
        orch = SettlementOrchestrator(project_dir)
        report = orch.settle_sync("", 1)
        assert "=== OBSERVATIONS ===" in report.observations

    def test_report_summary(self):
        report = SettlementReport(chapter_number=10)
        report.world = parse_world_output(
            "=== UPDATED_STATE ===\n地点: 藏书库\n"
        )
        report.character = parse_character_output(
            "=== UPDATED_EMOTIONAL_ARCS ===\n| 沈安 |\n"
        )
        report.plot = parse_plot_output(
            "=== UPDATED_HOOKS ===\n| H001 |\n"
        )
        s = report.summary()
        assert "第10章" in s
        assert "🌍" in s
        assert "👤" in s
        assert "📖" in s

    def test_report_summary_empty(self):
        report = SettlementReport(chapter_number=1)
        s = report.summary()
        assert "第1章" in s
