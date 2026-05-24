"""测试监控面板"""
import asyncio
import sys
import threading
import time
sys.path.insert(0, '/Users/agent/ai_os/src')

from discussion.engine import DiscussionEngine, DiscussionConfig
from discussion.monitor import DiscussionMonitor


def test_with_monitor():
    """带监控的测试"""
    # 创建监控器
    monitor = DiscussionMonitor(port=8765)
    
    # 创建引擎
    config = DiscussionConfig(max_rounds=2)
    engine = DiscussionEngine(config)
    
    # 注入监控回调
    engine.on_event = monitor.update
    
    # 启动监控面板
    monitor_thread = threading.Thread(target=monitor.run_dashboard, daemon=True)
    monitor_thread.start()
    
    print("\n📊 监控面板: http://localhost:8765")
    print("   按 Ctrl+C 结束\n")
    
    try:
        # 运行讨论
        asyncio.run(engine.run("是否先做demo验证方案可行性"))
    except KeyboardInterrupt:
        print("\n讨论已中断")
    finally:
        monitor.stop()


if __name__ == "__main__":
    test_with_monitor()