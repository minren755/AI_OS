"""快速测试讨论引擎"""
import asyncio
import sys
sys.path.insert(0, '/Users/agent/ai_os/src')
from discussion.engine import DiscussionEngine, DiscussionConfig


async def quick_test():
    # 只跑2轮
    config = DiscussionConfig(max_rounds=2)
    engine = DiscussionEngine(config)
    
    result = await engine.run("是否应该先做demo验证")
    
    print("\n" + "="*50)
    print("讨论结果:")
    for agent, state in result["Agent状态"].items():
        status = "✓满意" if state["满意"] else "待定"
        print(f"  {agent}: 发言{state['发言']}次, {status}")
    print(f"\n共识: {result['共识达成']}")


if __name__ == "__main__":
    asyncio.run(quick_test())