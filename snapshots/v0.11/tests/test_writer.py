"""
Writer Agent 测试
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_context_builder():
    """测试上下文组装"""
    print("=" * 50)
    print("测试: Context Builder")
    print("=" * 50)

    from src.utils.context_builder import ContextBuilder, ChapterContext

    # 用 unified_test 项目的上下文
    project_dir = os.path.join(os.path.dirname(__file__), "..", "projects", "unified_test")
    if not os.path.exists(project_dir):
        print("⚠️  unified_test 项目不存在，跳过（先运行 architect 生成）")
        return True

    builder = ContextBuilder(project_dir)
    ctx = builder.build(chapter_number=1)

    # 验证上下文包含各个部分
    context_text = ctx.build_prompt_context()
    assert len(context_text) > 100, "上下文不应为空"
    assert "故事设定" in context_text or "story_frame" in context_text.lower(), "应包含故事设定"
    print(f"✅ 上下文组装完成 ({len(context_text)} 字)")

    # 验证第1章的特殊处理
    ctx1 = builder.build(chapter_number=1)
    assert "第1章" in ctx1.chapter_summaries or "前情摘要" in ctx1.build_prompt_context()
    print(f"✅ 第1章上下文特殊处理正确")

    return True


def test_writer_agent_structure():
    """测试 Writer Agent 结构"""
    print("\n" + "=" * 50)
    print("测试: Writer Agent 结构")
    print("=" * 50)

    from src.agents.writer import WriterAgent, WRITER_SYSTEM_PROMPT
    from src.core.base_agent import AgentConfig

    agent = WriterAgent(AgentConfig(model_name="test"))
    assert agent.agent_name == "Writer"
    assert len(WRITER_SYSTEM_PROMPT) > 100
    assert "简体中文" in WRITER_SYSTEM_PROMPT
    print(f"✅ WriterAgent 实例化成功")
    print(f"   系统提示词: {len(WRITER_SYSTEM_PROMPT)} 字")

    return True


def test_writing_prompt_build():
    """测试写作 prompt 构建"""
    print("\n" + "=" * 50)
    print("测试: 写作 Prompt 构建")
    print("=" * 50)

    from src.utils.context_builder import ChapterContext

    # 构造模拟上下文
    ctx = ChapterContext(
        chapter_number=5,
        story_frame="这是一个测试故事框架。",
        roles="## 主角\n张三是一个勇敢的人。",
        pending_hooks="- [startChapter=0] 钩子A → 预计第10章回收",
        chapter_summaries="1. 第一章摘要\n2. 第二章摘要",
        user_guidance="本章需要有战斗场景",
    )

    from src.agents.writer import WriterAgent, WriterAgent as WriterCls
    agent = WriterCls()
    prompt = agent._build_writing_prompt(ctx, 5, 3000)

    assert "第 5 章" in prompt
    assert "3000" in prompt
    assert "故事设定" in prompt or "故事框架" in prompt
    assert "张三" in prompt
    assert "战斗场景" in prompt
    print(f"✅ prompt 构建正确 ({len(prompt)} 字)")

    return True


def test_state_manager():
    """测试状态管理器"""
    print("\n" + "=" * 50)
    print("测试: State Manager")
    print("=" * 50)

    from src.state.manager import StateManager

    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = StateManager(tmpdir)

        # 保存章节
        chapter_text = "这是测试章节的正文内容。共计约五十个字左右的测试文本。确保覆盖基本功能。"
        path = mgr.save_chapter(1, chapter_text)
        assert os.path.exists(path), f"章节文件未创建: {path}"
        print(f"✅ 章节保存成功: {path}")

        # 自动摘要
        summary = mgr.auto_summarize(chapter_text, 1)
        assert "1." in summary
        print(f"✅ 自动摘要: {summary[:50]}...")

        # 追加摘要
        mgr.append_summary(1, summary)
        summaries = open(os.path.join(tmpdir, "chapter_summaries.md"), encoding="utf-8").read()
        assert summary in summaries
        print(f"✅ 摘要已追加")

        # 检查 state 文件
        assert os.path.exists(os.path.join(tmpdir, "chapters", "chapter_0001.md"))
        assert os.path.exists(os.path.join(tmpdir, "chapter_summaries.md"))
        print(f"✅ 所有状态文件创建成功")

    return True


def main():
    print("\n🧪 Writer Agent 测试\n")

    tests = [
        test_context_builder,
        test_writer_agent_structure,
        test_writing_prompt_build,
        test_state_manager,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            print(f"\n❌ {test.__name__} 失败: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
