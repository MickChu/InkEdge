"""
模板系统专项测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_registry():
    """测试模板注册中心"""
    print("=" * 50)
    print("测试: 模板注册中心")
    print("=" * 50)

    from src.prompts import get_template_registry
    registry = get_template_registry()

    # 列出模板
    names = registry.list()
    assert "snowflake" in names, f"缺少 snowflake 模板，当前: {names}"
    print(f"✅ 注册的模板: {names}")

    # 获取模板集
    snowflake = registry.get("snowflake")
    assert snowflake is not None
    assert snowflake.display_name == "雪花写作法"
    assert snowflake.version == "1.0"
    print(f"✅ 模板集信息: {snowflake.display_name} v{snowflake.version}")

    # 获取步骤
    steps = snowflake.get_steps_in_order()
    assert len(steps) == 6, f"应有6个步骤，实际: {len(steps)}"
    print(f"✅ 步骤数: {len(steps)}")

    # 验证步骤顺序
    step_names = [s.name for s in steps]
    expected = ["核心种子", "角色动力学", "初始角色状态", "世界观构建", "情节架构", "章节目录"]
    for i, (actual, expected_name) in enumerate(zip(step_names, expected)):
        assert actual == expected_name, f"步骤 {i+1}: 期望 '{expected_name}', 实际 '{actual}'"
    print(f"✅ 步骤顺序正确: {step_names}")

    return True


def test_template_step_format():
    """测试模板步骤的参数填充"""
    print("\n" + "=" * 50)
    print("测试: 模板参数填充")
    print("=" * 50)

    from src.prompts import get_template_registry
    registry = get_template_registry()
    snowflake = registry.get("snowflake")

    # 测试 Step 1 的参数填充
    step1 = snowflake.get_step(1)
    assert step1 is not None
    prompt = step1.format_prompt(
        topic="测试主题",
        genre="科幻",
        number_of_chapters=10,
        word_number=3000,
    )
    assert "测试主题" in prompt
    assert "科幻" in prompt
    assert "10" in prompt
    assert "3000" in prompt
    print(f"✅ Step 1 填充成功 ({len(prompt)} 字符)")

    # 测试缺少必填参数时抛异常
    try:
        step1.format_prompt(topic="xx")
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "缺少必填参数" in str(e)
        print(f"✅ 缺少参数检测正常: {e}")

    # 测试 Step 5
    step5 = snowflake.get_step(5)
    assert step5 is not None
    prompt = step5.format_prompt(
        user_guidance="测试",
        novel_architecture="测试架构",
        number_of_chapters=10,
        character_names="张三、李四",
    )
    assert "测试架构" in prompt
    assert "10" in prompt
    print(f"✅ Step 5 填充成功 ({len(prompt)} 字符)")

    # 测试 output_file
    assert step5.output_file == "Novel_directory.txt"
    assert step1.output_file is None
    print(f"✅ output_file 属性正确")

    return True


def test_template_info():
    """测试模板集元信息"""
    print("\n" + "=" * 50)
    print("测试: 模板集元信息")
    print("=" * 50)

    from src.prompts import get_template_registry
    registry = get_template_registry()

    info = registry.list_with_info()
    assert len(info) == 2
    assert info[0]["name"] == "snowflake"
    assert info[0]["display_name"] == "雪花写作法"
    assert "Snowflake Method" in info[0]["description"]
    assert "通用" in info[0]["genres"]
    print(f"✅ 模板元信息完整: {info[0]['name']}={info[0]['display_name']}")


def test_add_future_template():
    """测试未来模板集的可扩展性"""
    print("\n" + "=" * 50)
    print("测试: 模板集扩展性")
    print("=" * 50)

    from src.prompts.base_template import TemplateStep, PromptTemplateSet, TemplateRegistry

    # 模拟添加一个新模板集
    registry = TemplateRegistry()
    new_template = PromptTemplateSet(
        name="save_the_cat",
        display_name="救猫咪节拍表",
        version="1.0",
        description="Blake Snyder 的 15 节拍故事结构",
        genres=["通用", "影视"],
        steps=[
            TemplateStep(
                order=1,
                name="开场画面",
                description="故事开始前的世界状态",
                required_params=["topic"],
                output_key="opening_image",
                prompt="为故事 '{topic}' 设计开场画面...",
            ),
            TemplateStep(
                order=2,
                name="主题陈述",
                description="暗示故事主题的对话或场景",
                required_params=["topic", "opening_image"],
                output_key="theme_statement",
                prompt="基于 '{opening_image}'，为主题 '{topic}' 写主题陈述...",
            ),
        ],
    )
    registry.register(new_template)

    assert "save_the_cat" in registry.list()
    save_cat = registry.get("save_the_cat")
    assert save_cat.display_name == "救猫咪节拍表"
    assert len(save_cat.get_steps_in_order()) == 2
    print(f"✅ 新模板集注册成功: {save_cat.display_name}")
    print(f"   步骤: {[s.name for s in save_cat.get_steps_in_order()]}")

    return True


def main():
    print("\n🧪 模板系统专项测试\n")

    tests = [
        test_registry,
        test_template_step_format,
        test_template_info,
        test_add_future_template,
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
