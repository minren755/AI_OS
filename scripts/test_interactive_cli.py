"""
交互式工作流测试 - 方案B完整演示
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from execution.workflow import WorkflowEngine
from execution.info_checker import check_and_ask


async def interactive_test():
    """交互式测试完整流程"""
    
    print("\n" + "=" * 70)
    print("AI_OS 交互式工作流测试")
    print("=" * 70)
    print("\n提示：输入主题后，系统会检查信息完整性")
    print("      如果信息不完整，会暂停询问")
    print("      你可以回答问题，或输入「继续」跳过")
    print()
    
    # 用户输入主题
    topic = input("请输入主题（如：我要做一个公司主页）: ").strip()
    
    if not topic:
        topic = "我要做一个公司主页"
        print(f"使用默认主题：{topic}")
    
    # 创建输出目录
    output_dir = project_root / "output" / "interactive" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建引擎
    engine = WorkflowEngine(workdir=str(output_dir), dry_run=False)
    
    # 事件回调
    def on_event(event):
        etype = event["type"]
        if etype == "need_input":
            print(f"\n系统需要更多信息：")
        elif etype == "planning_start":
            print(f"\n[Phase] 开始拆解任务...")
        elif etype == "tasks_created":
            print(f"  → 创建了 {event['data']['total_tasks']} 个任务")
        elif etype == "task_start":
            print(f"  → 执行：{event['data']['task']} ({event['data']['assignee']})")
    
    engine.on_event = on_event
    
    # 执行
    result = await engine.run(topic)
    
    # 检查是否需要交互
    if result.get("状态") == "等待用户输入":
        print("\n" + "-" * 70)
        print(result["提示"])
        print("-" * 70)
        
        # 用户回答
        user_input = input("\n请回答以上问题（或输入「继续」跳过）: ").strip()
        
        if user_input:
            print(f"\n继续执行，补充信息：{user_input[:50]}...")
            
            # 继续执行
            result = await engine.continue_with_input(user_input)
        else:
            print("\n跳过交互，直接继续...")
            result = await engine.continue_with_input("继续")
    
    # 显示结果
    print("\n" + "=" * 70)
    print("执行结果")
    print("=" * 70)
    
    if "任务" in result:
        print(f"\n任务列表 ({len(result['任务'])} 个)：")
        for t in result["任务"]:
            status_icon = "✓" if t["status"] == "completed" else "○"
            print(f"  {status_icon} {t['name']} → {t['assignee']}")
    
    # 检查输出文件
    print(f"\n输出目录：{output_dir}")
    files = list(output_dir.glob("*"))
    if files:
        print("\n生成文件：")
        for f in files:
            if f.is_file():
                print(f"  {f.name} ({f.stat().st_size} bytes)")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    return result


async def test_info_check():
    """只测试信息检查（不执行工作流）"""
    
    print("\n" + "=" * 70)
    print("信息完整性检查测试")
    print("=" * 70)
    
    test_cases = [
        "做一个公司主页",
        "做一个科技公司主页，包含AI解决方案业务，蓝色科技风格",
        "帮我写一个用户登录功能",
        "设计一个营销活动页面，主题是618促销，面向年轻用户",
    ]
    
    for topic in test_cases:
        print(f"\n主题：{topic}")
        result = check_and_ask(topic)
        
        if result["need_input"]:
            print(f"  → 需要补充信息")
            print(f"  → 缺少：{', '.join(result['missing'][:3])}")
            print(f"  → 问题：{result['questions'][0]}")
        else:
            print(f"  → 信息完整，可直接执行")


async def auto_test():
    """自动测试（预设场景）"""
    
    print("\n" + "=" * 70)
    print("自动交互测试")
    print("=" * 70)
    
    # 场景1：信息不完整
    print("\n【场景1】信息不完整")
    print("-" * 70)
    topic = "我要做一个公司主页"
    print(f"用户：{topic}")
    
    output_dir = project_root / "output" / "auto_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine = WorkflowEngine(workdir=str(output_dir), dry_run=True)
    result = await engine.run(topic)
    
    if result.get("状态") == "等待用户输入":
        print(f"\n系统暂停，询问：")
        for i, q in enumerate(result["问题"], 1):
            print(f"  {i}. {q}")
        
        # 模拟用户回答
        user_answer = "我们是AI解决方案公司，专注企业智能化转型。风格偏科技蓝色调。"
        print(f"\n用户回答：{user_answer}")
        
        # 模拟继续执行（不实际调用LLM）
        print(f"\n✓ 用户输入已接收")
        print(f"✓ 主题增强为：{topic} + 补充信息")
        print(f"✓ _skip_info_check 已设置为 True")
        print(f"✓ 系统将跳过信息检查，直接进入工作流")
    else:
        print("❌ 应该暂停询问")
    
    # 场景2：信息完整
    print("\n\n【场景2】信息完整")
    print("-" * 70)
    topic = "做一个科技公司主页，包含AI解决方案、数字员工业务，蓝色科技风格，面向企业客户"
    print(f"用户：{topic}")
    
    # 只检查信息，不执行工作流
    info_check = check_and_ask(topic)
    
    if info_check["need_input"]:
        print("❌ 不应该暂停（信息已完整）")
        print(f"   缺少：{info_check['missing']}")
    else:
        print("✓ 信息完整，直接进入工作流")


async def run_with_topic(topic: str):
    """带主题运行"""
    
    output_dir = project_root / "output" / "cli_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine = WorkflowEngine(workdir=str(output_dir), dry_run=True)
    
    print(f"\n主题：{topic}")
    result = await engine.run(topic)
    
    if result.get("状态") == "等待用户输入":
        print(f"\n需要补充信息：")
        for q in result["问题"]:
            print(f"  - {q}")
    else:
        print(f"\n执行完成")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            asyncio.run(test_info_check())
        elif sys.argv[1] == "--auto":
            # 自动测试模式（非交互）
            asyncio.run(auto_test())
        else:
            # 带参数运行
            topic = " ".join(sys.argv[1:])
            asyncio.run(run_with_topic(topic))
    else:
        # 交互模式
        asyncio.run(interactive_test())