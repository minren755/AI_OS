"""
测试PM两阶段拆解功能（离线模式，使用fallback逻辑）
"""
from execution.agents import Task
from execution.workflow import WorkflowEngine


def test_fallback_planning():
    """测试fallback拆解逻辑（不调用LLM）"""
    
    test_decisions = [
        "开发一个用户登录功能，支持邮箱注册、密码登录、第三方登录",
        "搭建一个博客系统，包含文章发布、评论、标签分类",
    ]
    
    engine = WorkflowEngine()
    
    for decision in test_decisions:
        print(f"\n{'='*60}")
        print(f"决策: {decision}")
        print(f"{'='*60}")
        
        # 直接测试fallback逻辑
        modules = engine._default_modules(decision)
        print(f"\n默认模块: {len(modules)} 个")
        for m in modules:
            print(f"  - {m['name']} (优先级: {m['priority']})")
        
        all_tasks = []
        for module in modules:
            tasks = engine._default_module_tasks(module)
            all_tasks.extend(tasks)
        
        # 建立跨模块依赖
        all_tasks = engine._link_cross_module_deps(all_tasks, modules)
        
        print(f"\n拆解任务: {len(all_tasks)} 个")
        for task in all_tasks:
            deps = f" (依赖: {task.dependencies})" if task.dependencies else ""
            print(f"  [{task.id}] {task.name} → {task.assignee}{deps}")
            if task.acceptance_criteria:
                print(f"       验收: {', '.join(task.acceptance_criteria)}")


if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))
    os.chdir(project_root)
    
    test_fallback_planning()
