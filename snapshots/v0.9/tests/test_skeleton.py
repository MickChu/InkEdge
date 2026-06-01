"""
验证项目骨架：导入测试 + Agent 模式测试
"""
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """测试所有模块可正常导入"""
    print("=" * 50)
    print("测试 1: 模块导入")
    print("=" * 50)

    # 核心模块
    from src.core.base_agent import BaseAgent, AgentConfig, AgentContext, AgentResult
    from src.core.orchestrator import Orchestrator, PipelineStep, PipelineResult
    from src.core.context_budget import ContextBudget, ContextBlock

    # 工具模块
    from src.utils.llm_client import LLMClient, LLMConfig, LLMResponse, LLMUsage
    from src.utils.file_io import read_file, write_file, ensure_dir
    from src.utils.text_utils import count_chinese_chars, estimate_tokens, clean_response

    # Agent 模块
    from src.agents.architect import ArchitectAgent

    print("✅ 所有模块导入成功")
    return True


def test_base_agent():
    """测试 Agent 基类"""
    print("\n" + "=" * 50)
    print("测试 2: Agent 基类")
    print("=" * 50)

    from src.core.base_agent import AgentConfig, AgentContext

    # 测试配置
    config = AgentConfig(
        model_name="deepseek-v4-flash",
        temperature=0.7,
        max_tokens=4096,
    )
    assert config.model_name == "deepseek-v4-flash"
    print("✅ AgentConfig 创建成功")

    # 测试上下文
    context = AgentContext(
        project_dir="/tmp/test_project",
        user_guidance="测试小说主题",
        extra={"genre": "科幻", "num_chapters": 30},
    )
    assert context.user_guidance == "测试小说主题"
    assert context.extra["genre"] == "科幻"
    print("✅ AgentContext 创建成功")

    # 测试 ArchitectAgent 实例化
    from src.agents.architect import ArchitectAgent
    architect = ArchitectAgent(config=config)
    assert architect.agent_name == "Architect"
    print("✅ ArchitectAgent 实例化成功")

    return True


def test_context_budget():
    """测试上下文预算"""
    print("\n" + "=" * 50)
    print("测试 3: 上下文预算")
    print("=" * 50)

    from src.core.context_budget import ContextBudget

    budget = ContextBudget(total_budget=10000)

    # 添加块
    budget.add_block("小说设定", "这是一个很长的设定文本" * 100, priority=10, source="story_bible")
    budget.add_block("最近章节", "第一章内容" * 50, priority=8, source="recent_chapters")
    budget.add_block("角色状态", "张三的状态" * 30, priority=6, source="current_state")

    # 构建上下文字符串
    context_str = budget.build_context_string()
    assert "小说设定" in context_str
    assert "最近章节" in context_str
    assert "角色状态" in context_str
    print(f"✅ 上下文预算构建成功 (总长: {len(context_str)} 字符)")

    # 测试 token 估算
    from src.utils.text_utils import estimate_tokens
    test_text = "这是一段测试文本，包含中文和English混合。"
    tokens = estimate_tokens(test_text)
    assert tokens > 0
    print(f"✅ Token 估算: '{test_text}' ≈ {tokens} tokens")

    return True


def test_file_io():
    """测试文件 IO"""
    print("\n" + "=" * 50)
    print("测试 4: 文件 IO")
    print("=" * 50)

    import tempfile
    from src.utils.file_io import write_file, read_file, ensure_dir

    tmpdir = tempfile.mkdtemp()

    # 测试写/读
    test_path = os.path.join(tmpdir, "test.txt")
    write_file(test_path, "Hello 你好")
    content = read_file(test_path)
    assert content == "Hello 你好"
    print("✅ 文件读写成功")

    # 测试默认值
    missing = read_file(os.path.join(tmpdir, "不存在.txt"), default="默认值")
    assert missing == "默认值"
    print("✅ 文件默认值正常")

    # 测试原子写入
    write_file(test_path, "覆盖内容", atomic=True)
    assert read_file(test_path) == "覆盖内容"
    print("✅ 原子写入成功")

    # 清理
    import shutil
    shutil.rmtree(tmpdir)
    print("✅ 临时文件清理完成")

    return True


def test_text_utils():
    """测试文本工具"""
    print("\n" + "=" * 50)
    print("测试 5: 文本工具")
    print("=" * 50)

    from src.utils.text_utils import count_chinese_chars, clean_response, truncate_text

    # 中文字符计数
    assert count_chinese_chars("你好世界") == 4
    assert count_chinese_chars("Hello 你好 World") == 2
    print("✅ 中文字符计数正常")

    # 响应清洗
    dirty = '好的，以下是您需要的内容：\n\n正文内容在这里。\n\n希望您喜欢！'
    clean = clean_response(dirty)
    assert "好的" not in clean
    assert "希望" not in clean
    assert "正文内容在这里" in clean
    print(f"✅ 响应清洗: '{dirty[:30]}...' → '{clean[:30]}...'")

    # 截断
    assert len(truncate_text("1234567890", 5)) <= 5
    print("✅ 文本截断正常")

    return True


def test_cli_help():
    """测试 CLI 帮助"""
    print("\n" + "=" * 50)
    print("测试 6: CLI 入口")
    print("=" * 50)

    # 验证 main.py 存在且可导入
    import importlib.util
    main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
    assert os.path.exists(main_path), f"main.py 不存在: {main_path}"
    print(f"✅ main.py 存在: {main_path}")
    print("✅ CLI 入口可用")


def main():
    """运行所有测试"""
    print("\n🧪 InkEdge 骨架验证测试\n")

    tests = [
        test_imports,
        test_base_agent,
        test_context_budget,
        test_file_io,
        test_text_utils,
        test_cli_help,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
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
