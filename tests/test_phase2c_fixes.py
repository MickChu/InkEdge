"""
Phase 2c 修复验证测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_system():
    """修复 1: Config 系统"""
    print("=" * 50)
    print("修复 1: Config 系统")
    print("=" * 50)

    from src.utils.config import ConfigManager, DEFAULT_CONFIG

    # 基本加载
    mgr = ConfigManager()
    assert mgr.get("default_genre") == "奇幻"
    assert mgr.get("default_chapters") == 60
    print("✅ 默认配置加载正常")

    # 运行时设置
    mgr.set("api_key", "sk-test-key")
    assert mgr.get("api_key") == "sk-test-key"
    print("✅ 运行时设置正常")

    # 脱敏
    mgr.set("api_key", "sk-123abcdef")
    masked = mgr.mask_sensitive(mgr.all())
    assert "…" in masked["api_key"]
    print(f"✅ 敏感字段脱敏: {masked['api_key']}")

    # 验证文件配置已加载
    assert mgr.get("default_template") == "unified"
    print(f"✅ 读取 config.yaml: default_template={mgr.get('default_template')}")

    return True


def test_character_name_extraction():
    """修复 3: 角色名提取与去重"""
    print("\n" + "=" * 50)
    print("修复 3: 角色名一致性")
    print("=" * 50)

    from src.utils.text_utils import extract_character_names

    # 模拟 Step 2 输出
    character_text = """## 角色一：沈墨（发明者）
### 1. 基础档案
- **姓名**：沈墨，字玄青
- **年龄**：27岁

## 角色二：赵元桢（改革皇子）
### 1. 基础档案
- **姓名**：赵元桢

## 角色三：苏檀儿（手工业主之女）
### 1. 基础档案
- **姓名**：苏檀儿

## 角色四：王伯渊（保守派宰相）
### 1. 基础档案
- **姓名**：王伯渊
"""

    names = extract_character_names(character_text)
    assert "沈墨" in names, f"应该提取到沈墨，实际: {names}"
    assert "赵元桢" in names
    assert "苏檀儿" in names
    assert "王伯渊" in names
    # 不应该有带括号的名字
    assert "沈墨（发明者）" not in names, f"括号未剥离: {names}"
    assert "沈墨，字玄青" not in names, f"字未过滤: {names}"
    print(f"✅ 角色名提取（已去括号）: {names}")

    # 中文数字格式
    text2 = "## 角色一：张三\n## 角色二：李四\n## 角色三：王五"
    names2 = extract_character_names(text2)
    assert "张三" in names2 and "李四" in names2
    print(f"✅ 中文数字格式: {names2}")

    # 【】格式
    text3 = "【沈墨】\n├── 物品\n│   ├── 西域机关密录"
    names3 = extract_character_names(text3)
    assert "沈墨" in names3
    print(f"✅ 【】格式: {names3}")

    return True


def test_worldbuilding_flexibility():
    """修复 2: 世界观灵活性"""
    print("\n" + "=" * 50)
    print("修复 2: 世界观灵活性")
    print("=" * 50)

    from src.prompts import get_template_registry
    registry = get_template_registry()
    snowflake = registry.get("snowflake")

    step3 = snowflake.get_step(3)
    assert step3 is not None

    prompt_text = step3.prompt
    # 核心：不应强制三维框架
    assert "不要套用任何固定框架" in prompt_text
    assert "物理维度" not in prompt_text
    assert "社会维度" not in prompt_text
    assert "隐喻维度" not in prompt_text
    assert "每个维度" not in prompt_text

    # 应有类型感知和自适应指导
    assert "genre" in prompt_text
    assert "genre}" in prompt_text
    assert "character_names" in prompt_text

    print(f"✅ 世界观 prompt 已去公式化")
    print(f"   关键指导: '不要套用任何固定框架'")
    print(f"   必填参数: {step3.required_params}")
    print(f"   可选参数: {step3.optional_params}")

    # 验证后续步骤也接受角色名
    step4 = snowflake.get_step(4)
    assert "character_names" in step4.required_params
    print(f"✅ Step 4 情节架构接受角色名约束")

    step5 = snowflake.get_step(5)
    assert "character_names" in step5.required_params
    print(f"✅ Step 5 章节目录接受角色名约束")

    return True


def test_llm_client_config_integration():
    """集成: LLMClient 通过配置读取 API Key"""
    print("\n" + "=" * 50)
    print("集成: LLMClient 配置集成")
    print("=" * 50)

    from src.utils.llm_client import LLMClient

    # 无 env var，应回退到 config.yaml（默认为空）
    client = LLMClient()
    base_url = client._get_base_url()
    assert "deepseek" in base_url
    print(f"✅ base_url: {base_url}")

    # 实例参数优先级最高
    client2 = LLMClient(api_key="sk-local-key", base_url="https://custom.api.com/v1")
    assert client2._get_api_key() == "sk-local-key"
    assert client2._get_base_url() == "https://custom.api.com/v1"
    print(f"✅ 实例参数优先级: api_key={client2._get_api_key()[:4]}***, url={client2._get_base_url()}")

    return True


def main():
    print("\n🧪 Phase 2c 修复验证\n")

    tests = [
        test_config_system,
        test_character_name_extraction,
        test_worldbuilding_flexibility,
        test_llm_client_config_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
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
