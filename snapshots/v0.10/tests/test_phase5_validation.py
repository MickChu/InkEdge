"""
Phase 5 测试 — 后验校验系统
"""
import os
import sys
import tempfile
import shutil
import pytest

# 将项目根加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSegmentation:
    """文本分段测试"""

    def test_simple_paragraphs(self):
        from src.validation.duplication import _segment_text
        text = "段落一的内容在这里。\n\n段落二的内容在这里。\n\n段落三是比较长的内容。"
        segs = _segment_text(text, min_chars=5, max_chars=200)
        assert len(segs) >= 1


    def test_short_text_merged(self):
        from src.validation.duplication import _segment_text
        text = "短。"
        segs = _segment_text(text, min_chars=5, max_chars=200)
        assert len(segs) == 0


    def test_long_paragraph_not_split(self):
        from src.validation.duplication import _segment_text
        # 一个没有空行分割的超长段落 → 不强制分割
        long_para = "长文本。" * 300
        segs = _segment_text(long_para, min_chars=80, max_chars=600)
        assert len(segs) == 1
        assert len(segs[0]) > 600


class TestAIStyleScorer:
    """AI 痕迹评分测试"""

    def test_clean_text_scores_low(self):
        from src.validation.ai_style import AIStyleScorer
        scorer = AIStyleScorer()
        text = """天色暗下来的时候，街道两侧的灯次第亮了。行人渐少，偶尔有自行车响着铃从身边擦过。老旧小区的楼道里飘着炒菜的油烟味，混合着谁家电视的声响。王建国站在单元门口，把烟头踩灭，推门进去。楼梯间的声控灯坏了两盏，他借着手机屏幕的光往上走。三楼左转，防盗门上的春联褪成了粉白色。他摸出钥匙，在锁孔里转了两圈——门没反锁。"""
        result = scorer.score(text)
        # 好文本得分应该低
        assert result.score < 40
        assert result.level != "严重"


    def test_ai_text_scores_high(self):
        from src.validation.ai_style import AIStyleScorer
        scorer = AIStyleScorer()
        text = """值得注意的是，在这个世界中，主角展现出了非凡的能力。突然，他发现了隐藏在暗处的敌人。竟然有着如此强大的力量，这让他感到十分震惊。与此同时，另一股势力也在暗中观察着这一切。紧接着，战斗不可避免地爆发了。可以看出，主角的成长速度非常快。"""
        result = scorer.score(text)
        # AI 套话密集 → 高分
        assert result.score > 20


    def test_dialogue_absence_detected(self):
        from src.validation.ai_style import AIStyleScorer
        scorer = AIStyleScorer()
        text = "今天天气很好。他走在路上想着心事。远处的山峦起伏。风吹过树梢发出沙沙的声音。他停下脚步看了看四周。然后继续往前走。"
        result = scorer.score(text)
        assert result.dialogue_ratio < 0.1


    def test_blacklist_keywords_detected(self):
        from src.validation.ai_style import AIStyleScorer
        scorer = AIStyleScorer()
        text = "值得注意的是这是一个测试。突然出现的情况十分意外。竟然会发生这种事。综上所述没有问题。"
        result = scorer.score(text)
        assert len(result.blacklist_hits) >= 1


class TestConsistencyValidator:
    """一致性校验测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_project_files(self, roles="", rules="", hooks=""):
        if roles:
            with open(os.path.join(self.tmpdir, "roles.md"), "w", encoding="utf-8") as f:
                f.write(roles)
        if rules:
            with open(os.path.join(self.tmpdir, "book_rules.md"), "w", encoding="utf-8") as f:
                f.write(rules)
        if hooks:
            with open(os.path.join(self.tmpdir, "pending_hooks.md"), "w", encoding="utf-8") as f:
                f.write(hooks)

    def test_empty_project_passes(self):
        from src.validation.consistency import ConsistencyValidator
        v = ConsistencyValidator(self.tmpdir)
        result = v.validate("任意文本", 1)
        assert result.passed

    def test_known_roles_dont_trigger_false_alarm(self):
        from src.validation.consistency import ConsistencyValidator
        self._write_project_files(roles="name: 沈安\nname: 苏若兰\nname: 老铁匠\n")
        v = ConsistencyValidator(self.tmpdir)
        result = v.validate("沈安走到苏若兰面前。老铁匠在一旁看着。", 1)
        # 角色名都出现，不应报未知名
        assert result.passed

    def test_rule_violation_detected(self):
        from src.validation.consistency import ConsistencyValidator
        self._write_project_files(rules="prohibitions:\n  - 禁止出现飞行的剑\n")
        v = ConsistencyValidator(self.tmpdir)
        result = v.validate("主角手一挥，一把飞行的剑从背后飞出。", 1)
        assert not result.passed
        assert any("飞行的剑" in i.description for i in result.issues)

    def test_rules_without_prohibition_passes(self):
        from src.validation.consistency import ConsistencyValidator
        self._write_project_files(rules="rules:\n  - 灵力等级体系：炼气→筑基→金丹→元婴\n")
        v = ConsistencyValidator(self.tmpdir)
        result = v.validate("主角突破了筑基境界。", 1)
        assert result.passed

    def test_hook_due_reminder(self):
        from src.validation.consistency import ConsistencyValidator
        self._write_project_files(hooks="""[startChapter=3] 沈安发现暗格中的密信
→ 预计回收 第1卷

[startChapter=8] 苏若兰体内留下追踪印记
→ 预计回收 第2卷
""")
        v = ConsistencyValidator(self.tmpdir)
        result = v.validate("一些无关内容", 25)  # 第25章应该是第2卷
        # 第8章的伏笔应在本卷回收（第21-40章属于第2卷）
        has_hook_issue = any(i.issue_type == "hook" for i in result.issues)
        assert has_hook_issue


class TestCheckOrchestrator:
    """编排器集成测试"""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self._write_foundation()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_foundation(self):
        os.makedirs(os.path.join(self.tmpdir, "chapters"), exist_ok=True)
        with open(os.path.join(self.tmpdir, "roles.md"), "w", encoding="utf-8") as f:
            f.write("name: 沈安\nname: 苏若兰\n")
        with open(os.path.join(self.tmpdir, "book_rules.md"), "w", encoding="utf-8") as f:
            f.write("rules:\n  - 禁止时间穿越\n")
        with open(os.path.join(self.tmpdir, "pending_hooks.md"), "w", encoding="utf-8") as f:
            f.write("")

    def test_full_report_no_vectorstore(self):
        from src.validation.checker import CheckOrchestrator
        checker = CheckOrchestrator(self.tmpdir)
        text = """夜色浓重。沈安沿着城墙根快步走着，斗篷在风中鼓动。苏若兰在后面不远不近地跟着，每一步都踩在石板间的缝隙里。两人没有说话，但都知道彼此在想什么——天亮之前，必须出城。"""
        report = checker.run(text, chapter_number=2, project_name="test")
        assert report.chapter_number == 2
        assert report.ai_style is not None
        assert report.consistency is not None
        # 无 VectorStore → 重复检测跳过
        assert report.duplication is not None

    def test_format_cli_output(self):
        from src.validation.checker import CheckOrchestrator
        checker = CheckOrchestrator(self.tmpdir)
        text = "简单测试文本。"
        report = checker.run(text, chapter_number=1, project_name="test")
        output = report.format_cli()
        assert "test" in output
        assert "第1章" in output

    def test_skip_options(self):
        from src.validation.checker import CheckOrchestrator
        checker = CheckOrchestrator(
            self.tmpdir,
            skip_ai_style=True,
            skip_consistency=True,
        )
        text = "任意文本"
        report = checker.run(text, chapter_number=1, project_name="test")
        # AI 痕迹被跳过
        assert report.ai_style is None or report.ai_style.level == "未知"
        # 一致性被跳过
        assert report.consistency is None or report.consistency.passed


class TestReportFormatting:
    """报告格式化测试"""

    def test_format_includes_basic_info(self):
        from src.validation.report import CheckReport
        from src.validation.ai_style import AIStyleReport
        report = CheckReport(
            project_name="test_proj",
            chapter_number=3,
            word_count=1500,
            ai_style=AIStyleReport(score=10, level="良好", total_words=1500),
        )
        output = report.format_cli()
        assert "test_proj" in output
        assert "第3章" in output

    def test_has_errors_on_duplication(self):
        from src.validation.report import CheckReport, DuplicationReport, DuplicateHit
        report = CheckReport(
            duplication=DuplicationReport(
                passed=False,
                hits=[DuplicateHit(
                    new_segment="test", matched_segment="test",
                    similarity=0.95, source_chapter=1, severity="high",
                )],
            ),
        )
        assert report.has_errors()

    def test_no_errors_on_clean(self):
        from src.validation.report import CheckReport, DuplicationReport
        report = CheckReport(
            duplication=DuplicationReport(passed=True),
        )
        assert not report.has_errors()
