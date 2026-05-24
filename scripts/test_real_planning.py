"""
测试PM两阶段拆解 - 真实LLM调用
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from execution.workflow import WorkflowEngine


async def test_real_planning():
    """真实LLM测试"""
    
    decision = "开发一个简单的用户登录功能"
    
    print(f"测试决策: {decision}")
    print("=" * 50)
    
    engine = WorkflowEngine()
    
    # 只测试规划阶段
    print("\n[Phase 2.1] 拆模块...")
    modules = await engine._plan_modules(decision)
    
    print(f"模块数: {len(modules)}")
    for m in modules:
        print(f"  - {m['name']} (优先级={m['priority']}, 预计{m.get('estimated_tasks', 3)}任务)")
    
    print("\n[Phase 2.2] 每模块拆任务...")
    all_tasks = []
    for module in modules:
        tasks = await engine._plan_module_tasks(module, decision)
        all_tasks.extend(tasks)
        print(f"  {module['name']}: {len(tasks)}个任务")
    
    # 建立依赖
    all_tasks = engine._link_cross_module_deps(all_tasks, modules)
    
    print(f"\n总任务: {len(all_tasks)}")
    print("-" * 50)
    
    for task in all_tasks:
        print(f"[{task.id}] {task.name}")
        print(f"   执行者: {task.assignee} | 优先级: {task.priority}")
        if task.acceptance_criteria:
            print(f"   验收: {task.acceptance_criteria[0]}")
        if task.dependencies:
            print(f"   依赖: {task.dependencies}")
        print()


if __name__ == "__main__":
    asyncio.run(test_real_planning())