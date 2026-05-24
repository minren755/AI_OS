"""
测试方案B - PM层交互检查
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from execution.workflow import WorkflowEngine


async def test_interactive_workflow():
    """测试交互式工作流"""
    
    print("\n" + "=" * 70)
    print("测试方案B - PM层交互检查")
    print("=" * 70)
    
    # 创建引擎
    engine = WorkflowEngine(workdir=str(project_root / "output" / "interactive_test"), dry_run=True)
    
    # 设置事件回调
    def on_event(event):
        if event["type"] == "need_input":
            print(f"\n系统：{event['data']['prompt']}")
    
    engine.on_event = on_event
    
    # 测试场景1：信息不完整
    print("\n【场景1】信息不完整的请求")
    print("-" * 70)
    print("用户：我要做一个公司主页")
    
    result = await engine.run("我要做一个公司主页")
    
    if result.get("状态") == "等待用户输入":
        print(f"\n✓ 系统暂停，等待输入")
        print(f"问题：{result['问题']}")
        print(f"\n提示：{result['提示']}")
        
        # 模拟用户回答
        user_answer = "我们是AI解决方案公司，专注企业智能化转型。"
        print(f"\n用户回答：{user_answer}")
        
        # 验证状态
        print(f"\n✓ waiting_for_input = {engine.waiting_for_input}")
        print(f"✓ user_responses = {engine.user_responses}")
    else:
        print("❌ 应该暂停等待输入")
    
    # 测试场景2：信息完整
    print("\n\n【场景2】信息完整的请求")
    print("-" * 70)
    print("用户：做一个科技公司主页，包含AI解决方案、数字员工业务，蓝色科技风格")
    
    # 只测试信息检查（不实际执行）
    from execution.info_checker import check_and_ask
    info_check = check_and_ask("做一个科技公司主页，包含AI解决方案、数字员工业务，蓝色科技风格")
    
    if info_check["need_input"]:
        print("❌ 不应该暂停（信息已完整）")
        print(f"   缺少：{info_check['missing']}")
    else:
        print("✓ 信息完整，直接执行")


async def test_info_checker():
    """测试信息检查器"""
    
    print("\n" + "=" * 70)
    print("测试信息检查器")
    print("=" * 70)
    
    from execution.info_checker import InfoChecker
    
    checker = InfoChecker()
    
    test_cases = [
        ("做一个公司主页", "信息少"),
        ("做一个科技公司主页，包含AI解决方案业务", "有业务"),
        ("做一个科技公司主页，蓝色科技风格，目标用户是企业", "有风格+用户"),
        ("做一个科技公司主页，包含AI业务，蓝色风格，面向企业客户，需要联系我们模块", "信息完整"),
    ]
    
    for topic, desc in test_cases:
        is_complete, missing = checker.check_completeness(topic)
        status = "✓ 完整" if is_complete else f"缺少: {missing}"
        print(f"\n{desc}: {topic[:30]}...")
        print(f"  {status}")


if __name__ == "__main__":
    print("\n测试信息检查器...")
    asyncio.run(test_info_checker())
    
    print("\n\n测试交互式工作流...")
    asyncio.run(test_interactive_workflow())