"""
测试四Agent（CEO+CFO+CTO+CMO）讨论流程

用法：
    cd /Users/agent/ai_os
    source venv/bin/activate
    python scripts/test_four_agents.py "议题"
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.four_agent_app import four_agent_app
from src.graph.state import AgentState


def run_four_agent_test(topic: str):
    """运行四Agent讨论测试"""
    print(f"🚀 AI_OS 四Agent测试启动")
    print(f"📝 议题: {topic}")
    print(f"👥 Agent: CEO → CFO → CTO → CMO")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
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
    result = four_agent_app.invoke(initial_state)
    
    # 输出结果
    print("\n📋 讨论记录:")
    print("-" * 60)
    
    # 按轮次分组显示
    rounds = {}
    for msg in result["messages"]:
        r = msg["round"]
        if r not in rounds:
            rounds[r] = []
        rounds[r].append(msg)
    
    for round_num in sorted(rounds.keys()):
        print(f"\n【第{round_num}轮】")
        for msg in rounds[round_num]:
            print(f"  [{msg['agent']}]: {msg['content'][:200]}...")
    
    print("\n" + "-" * 60)
    print(f"✅ 共识: {result['consensus']}")
    print(f"📊 总轮次: {result['round_count']}")
    print(f"💬 总消息数: {len(result['messages'])}")
    if result['decision']:
        print(f"🎯 决策: {result['decision'][:150]}...")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_four_agents.py \"议题\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    run_four_agent_test(topic)