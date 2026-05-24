"""
AI_OS CLI测试入口

用法：
    cd /Users/agent/ai_os
    source venv/bin/activate
    python scripts/run.py "讨论议题"
"""

import sys
import os

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime

from src.graph import app, AgentState


def run_discussion(topic: str) -> dict:
    """
    运行一次完整讨论
    """
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
    return result


def print_result(result: dict) -> None:
    """格式化输出讨论结果"""
    print("\n" + "=" * 60)
    print(f"  AI_OS 讨论结果")
    print("=" * 60)
    print(f"  议题: {result['topic']}")
    print(f"  轮次: {result['round_count']}")
    print(f"  共识: {'✅ 是' if result['consensus'] else '❌ 否'}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("\n📋 讨论过程：\n")
    for i, msg in enumerate(result["messages"], 1):
        agent = msg["agent"]
        content = msg["content"]
        print(f"  {i}. [{agent}]")
        for line in content.split("\n"):
            print(f"     {line}")
        print()
    
    if result.get("decision"):
        print(f"📌 决策结论: {result['decision']}")
    
    if result.get("dissent"):
        print(f"⚠️  分歧点: {result['dissent']}")
    
    print("\n" + "=" * 60)


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/run.py \"讨论议题\"")
        print('示例: python scripts/run.py "是否开发AI质检新功能"')
        sys.exit(1)
    
    topic = sys.argv[1]
    
    print(f"🚀 AI_OS 启动")
    print(f"📝 议题: {topic}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⏳ 讨论进行中...\n")
    
    result = run_discussion(topic)
    
    print_result(result)


if __name__ == "__main__":
    main()
