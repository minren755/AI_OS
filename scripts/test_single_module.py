"""
测试PM两阶段拆解 - 真实LLM调用（简化版）
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from execution.workflow import WorkflowEngine


async def test_single_module():
    """只测试单个模块拆解"""
    
    decision = "开发一个简单的用户登录功能"
    
    print(f"测试决策: {decision}")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    # 手动创建一个模块测试
    test_module = {
        "name": "用户认证",
        "description": "实现用户登录认证功能",
        "priority": 5
    }
    
    print("\n测试单个模块拆解...")
    tasks = await engine._plan_module_tasks(test_module, decision)
    
    print(f"\n拆解结果: {len(tasks)} 个任务")
    print("-" * 50)
    
    for task in tasks:
        print(f"[{task.id}] {task.name}")
        print(f"   执行者: {task.assignee} | 优先级: {task.priority}")
        if task.acceptance_criteria:
            print(f"   验收: {task.acceptance_criteria[0]}")


if __name__ == "__main__":
    asyncio.run(test_single_module())