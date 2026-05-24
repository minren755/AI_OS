"""
测试PM两阶段拆解功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 设置正确的导入路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from execution.agents import Task
from execution.workflow import WorkflowEngine


async def test_planning():
    """测试任务拆解"""
    
    # 模拟决策输出（来自决策层讨论）
    test_decisions = [
        "开发一个用户登录功能，支持邮箱注册、密码登录、第三方登录（微信）",
        "搭建一个博客系统，包含文章发布、评论、标签分类功能",
        "实现一个定时任务系统，支持cron表达式配置和任务执行日志"
    ]
    
    # 创建WorkflowEngine（dry-run模式，不实际执行）
    engine = WorkflowEngine(tool_executor=lambda t: None)
    
    for decision in test_decisions:
        print(f"\n{'='*60}")
        print(f"决策: {decision}")
        print(f"{'='*60}")
        
        # 只测试拆解阶段
        tasks = await engine._run_planning_phase(decision)
        
        print(f"\n拆解结果: {len(tasks)} 个任务\n")
        
        # 按模块分组显示
        modules = {}
        for task in tasks:
            if task.module not in modules:
                modules[task.module] = []
            modules[task.module].append(task)
        
        for module_name, module_tasks in modules.items():
            print(f"\n【{module_name}】")
            for task in module_tasks:
                print(f"  ├─ {task.id}: {task.name}")
                print(f"  │  执行者: {task.assignee} | 优先级: {task.priority} | 预计步骤: {task.estimated_steps}")
                if task.acceptance_criteria:
                    print(f"  │  验收标准: {', '.join(task.acceptance_criteria[:2])}")
                if task.dependencies:
                    print(f"  │  依赖: {task.dependencies}")
                print(f"  │")


if __name__ == "__main__":
    asyncio.run(test_planning())
