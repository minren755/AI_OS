"""
测试讨论引擎
"""
import asyncio
import sys
sys.path.insert(0, '/Users/agent/ai_os/src')

from discussion.engine import DiscussionEngine, DiscussionConfig


async def main():
    # 可自定义配置
    config = DiscussionConfig(
        max_rounds=5,
        context_window=2
    )
    
    engine = DiscussionEngine(config)
    
    # 从命令行获取议题
    topic = sys.argv[1] if len(sys.argv) > 1 else "是否应该先做demo验证方案可行性"
    
    result = await engine.run(topic)
    
    print("\n" + "="*60)
    print("讨论摘要:")
    print("="*60)
    for agent, state in result["Agent状态"].items():
        status = "✓满意" if state["满意"] else "待定"
        print(f"{agent}: 发言{state['发言次数']}次, 跳过{state['跳过次数']}次, {status}")
    
    print(f"\n共识达成: {result['共识达成']}")


if __name__ == "__main__":
    asyncio.run(main())