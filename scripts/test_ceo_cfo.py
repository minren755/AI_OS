"""
测试CEO+CFO Hermes Gateway集成

用法：
    cd /Users/agent/ai_os
    source venv/bin/activate
    python scripts/test_ceo_cfo.py "议题"
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.test_app import test_app
from src.graph.state import AgentState


def run_test(topic: str):
    """运行CEO+CFO讨论测试"""
    print(f"🚀 AI_OS 测试启动 (CEO+CFO)")
    print(f"📝 议题: {topic}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # 初始状态
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
    
    # 运行图
    result = test_app.invoke(initial_state)
    
    # 输出结果
    print("\n📋 讨论记录:")
    print("-" * 50)
    for msg in result["messages"]:
        print(f"[{msg['agent']}] (第{msg['round']}轮)")
        print(f"{msg['content']}")
        print()
    
    print("-" * 50)
    print(f"✅ 共识: {result['consensus']}")
    print(f"📊 总轮次: {result['round_count']}")
    if result['decision']:
        print(f"🎯 决策: {result['decision'][:100]}...")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_ceo_cfo.py \"议题\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    run_test(topic)