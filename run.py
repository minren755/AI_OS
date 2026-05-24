"""
AI_OS 统一CLI入口

用法：
    python run.py "议题"              # 动态讨论模式（推荐）
    python run.py "议题" --langgraph  # LangGraph流程模式
    python run.py "议题" --monitor    # 启动监控面板
"""
import sys
import os
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_dynamic_discussion(topic: str, max_rounds: int = 3) -> dict:
    """
    动态讨论模式（DiscussionEngine）
    - Agent可跳过发言
    - Agent可指定下一位
    - 自动共识检测
    """
    import asyncio
    from src.discussion.engine import DiscussionEngine, DiscussionConfig
    
    config = DiscussionConfig(max_rounds=max_rounds)
    engine = DiscussionEngine(config)
    
    print(f"\n{'='*60}")
    print(f"  模式: 动态讨论")
    print(f"  议题: {topic}")
    print(f"  最大轮数: {max_rounds}")
    print(f"  时间: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    result = asyncio.run(engine.run(topic))
    
    # 输出摘要
    print(f"\n{'='*60}")
    print(f"  讨论结束 {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    for agent, state in result["Agent状态"].items():
        status = "✓满意" if state["满意"] else "待定"
        print(f"  {agent}: 发言{state['发言']}次, 跳过{state['跳过']}次, {status}")
    
    print(f"\n  共识达成: {'✅ 是' if result['共识达成'] else '❌ 否'}")
    
    # 输出观点摘要
    if result["观点汇总"]:
        print(f"\n  📋 观点摘要:")
        for view in result["观点汇总"][:4]:  # 最多显示4条
            print(f"     [{view['agent']}] {view['content'][:60]}...")
    
    return result


def run_langgraph_discussion(topic: str) -> dict:
    """
    LangGraph流程模式
    - 固定顺序CEO→CFO→CTO→CMO
    - 状态机驱动
    """
    from src.graph import app, AgentState
    
    print(f"\n{'='*60}")
    print(f"  模式: LangGraph流程")
    print(f"  议题: {topic}")
    print(f"  时间: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    initial_state = AgentState(
        topic=topic,
        messages=[],
        round_count=0,
        consensus=False,
        decision="",
        dissent="",
        next_agent="CEO",
        tasks=[],
        results=[],
    )
    
    result = app.invoke(initial_state)
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f"  轮次: {result['round_count']}")
    print(f"  共识: {'✅ 是' if result['consensus'] else '❌ 否'}")
    print(f"{'='*60}\n")
    
    for i, msg in enumerate(result["messages"], 1):
        agent = msg["agent"]
        content = msg["content"][:80] + "..." if len(msg["content"]) > 80 else msg["content"]
        print(f"  {i}. [{agent}] {content}")
    
    return result


def run_with_monitor(topic: str, max_rounds: int = 3):
    """
    带监控面板的讨论模式
    """
    from src.discussion.engine import DiscussionEngine, DiscussionConfig
    from src.discussion.monitor import DiscussionMonitor
    
    monitor = DiscussionMonitor()
    config = DiscussionConfig(max_rounds=max_rounds)
    engine = DiscussionEngine(config)
    
    # 注入监控回调
    engine.on_message = monitor.update
    
    # 启动监控面板（异步）
    import threading
    monitor_thread = threading.Thread(target=monitor.run_dashboard, daemon=True)
    monitor_thread.start()
    
    print("\n📊 监控面板已启动: http://localhost:8765")
    print("   按 Ctrl+C 结束讨论\n")
    
    try:
        asyncio.run(engine.run(topic))
    except KeyboardInterrupt:
        print("\n讨论已中断")
    finally:
        monitor.stop()


def run_web_interface(port: int = 8765):
    """
    Web交互模式
    """
    from src.web.app import run_web_server
    run_web_server(port)


def run_workflow(topic: str, dry_run: bool = True):
    """
    工作流模式：讨论 → 拆解 → 执行
    dry_run=True: 不执行真实操作，只生成计划
    dry_run=False: 执行真实操作（需要工具执行器）
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from execution.workflow import WorkflowEngine
    
    async def _run():
        engine = WorkflowEngine()
        result = await engine.run(topic)
        print("\n" + "=" * 50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    asyncio.run(_run())


def main():
    parser = argparse.ArgumentParser(description="AI_OS 多Agent讨论系统")
    parser.add_argument("topic", nargs='?', help="讨论议题（Web模式不需要）")
    parser.add_argument("--web", "-w", action="store_true",
                       help="启动Web交互界面")
    parser.add_argument("--workflow", "-f", action="store_true",
                       help="工作流模式：讨论→拆解→执行")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="工作流模式下只生成计划，不执行")
    parser.add_argument("--port", "-p", type=int, default=8765,
                       help="Web服务器端口（默认8765）")
    parser.add_argument("--langgraph", "-l", action="store_true",
                       help="使用LangGraph流程模式")
    parser.add_argument("--monitor", "-m", action="store_true",
                       help="启动监控面板")
    parser.add_argument("--rounds", "-r", type=int, default=3,
                       help="最大讨论轮数（默认3）")
    
    args = parser.parse_args()
    
    if args.web:
        run_web_interface(args.port)
    elif args.workflow:
        if not args.topic:
            print("请提供议题: python run.py \"议题\" --workflow")
            sys.exit(1)
        run_workflow(args.topic, args.dry_run)
    elif args.monitor:
        run_with_monitor(args.topic, args.rounds)
    elif args.langgraph:
        if not args.topic:
            print("请提供议题: python run.py \"议题\" --langgraph")
            sys.exit(1)
        run_langgraph_discussion(args.topic)
    else:
        if not args.topic:
            print("用法:")
            print("  python run.py \"议题\"          # 动态讨论")
            print("  python run.py --web            # Web交互界面")
            print("  python run.py \"议题\" --monitor # 带监控面板")
            sys.exit(1)
        run_dynamic_discussion(args.topic, args.rounds)


if __name__ == "__main__":
    main()
