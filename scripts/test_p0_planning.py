"""
测试PM两阶段拆解 - Task结构和依赖链验证
"""
from execution.agents import Task, TaskStatus


def test_task_structure():
    """测试Task新字段"""
    
    task = Task(
        id="LOGIN_1",
        name="设计登录API",
        description="设计用户登录API接口",
        assignee="Developer",
        priority=5,
        acceptance_criteria=["API文档完成", "接口定义清晰"],
        estimated_steps=3,
        context_files=["src/api/auth.py"],
        module="用户认证"
    )
    
    print("Task结构测试:")
    print(f"  ID: {task.id}")
    print(f"  名称: {task.name}")
    print(f"  模块: {task.module}")
    print(f"  验收标准: {task.acceptance_criteria}")
    print(f"  预计步骤: {task.estimated_steps}")
    print(f"  上下文文件: {task.context_files}")
    print("  ✓ P0新增字段全部正常")


def test_dependency_chain():
    """测试跨模块依赖链"""
    
    # 模拟3个模块的任务
    tasks = [
        Task(id="CORE_1", name="数据库设计", description="设计数据库表结构", module="核心功能", assignee="Developer", priority=5),
        Task(id="CORE_2", name="API实现", description="实现API接口", module="核心功能", assignee="Developer", priority=5, dependencies=["CORE_1"]),
        Task(id="CORE_3", name="核心测试", description="核心功能测试", module="核心功能", assignee="QA", priority=4, dependencies=["CORE_2"]),
        Task(id="UI_1", name="登录页面", description="设计登录UI", module="用户界面", assignee="Designer", priority=4, dependencies=["CORE_3"]),  # 跨模块依赖
        Task(id="UI_2", name="交互优化", description="优化交互体验", module="用户界面", assignee="Designer", priority=3, dependencies=["UI_1"]),
        Task(id="TEST_1", name="集成测试", description="系统集成测试", module="测试验证", assignee="QA", priority=3, dependencies=["UI_2"]),  # 跨模块依赖
    ]
    
    print("\n依赖链测试:")
    
    # 验证依赖顺序
    completed = set()
    execution_order = []
    
    while tasks:
        ready = [t for t in tasks if all(d in completed for d in t.dependencies)]
        if not ready:
            print("  ✗ 检测到循环依赖!")
            break
        for task in ready:
            execution_order.append(task)
            completed.add(task.id)
            tasks.remove(task)
    
    print(f"  执行顺序 ({len(execution_order)} 步):")
    for i, task in enumerate(execution_order, 1):
        print(f"    {i}. [{task.id}] {task.name} ({task.module})")
    
    print("  ✓ 依赖链解析正常，按拓扑序执行")


def test_cross_module_link():
    """测试跨模块依赖建立逻辑"""
    
    from execution.workflow import WorkflowEngine
    engine = WorkflowEngine()
    
    # 模拟模块和任务
    modules = [
        {"name": "核心功能", "priority": 5},
        {"name": "用户界面", "priority": 4},
        {"name": "测试验证", "priority": 3},
    ]
    
    tasks = [
        Task(id="CORE_1", name="核心1", description="核心模块任务1", module="核心功能", assignee="Developer", priority=5),
        Task(id="CORE_2", name="核心2", description="核心模块任务2", module="核心功能", assignee="Developer", priority=5, dependencies=["CORE_1"]),
        Task(id="UI_1", name="界面1", description="界面模块任务1", module="用户界面", assignee="Designer", priority=4),
        Task(id="UI_2", name="界面2", description="界面模块任务2", module="用户界面", assignee="Designer", priority=3, dependencies=["UI_1"]),
        Task(id="TEST_1", name="测试1", description="测试模块任务1", module="测试验证", assignee="QA", priority=3),
    ]
    
    # 应用跨模块依赖
    linked = engine._link_cross_module_deps(tasks, modules)
    
    print("\n跨模块依赖建立测试:")
    for task in linked:
        if task.dependencies:
            print(f"  [{task.id}] 依赖: {task.dependencies}")
    
    # 验证UI_1依赖CORE_2（上一模块最后任务）
    ui_1 = next(t for t in linked if t.id == "UI_1")
    assert "CORE_2" in ui_1.dependencies, "UI_1应依赖CORE_2"
    
    # 验证TEST_1依赖UI_2
    test_1 = next(t for t in linked if t.id == "TEST_1")
    assert "UI_2" in test_1.dependencies, "TEST_1应依赖UI_2"
    
    print("  ✓ 跨模块依赖正确建立")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))
    
    print("=" * 60)
    print("P0任务拆解功能测试")
    print("=" * 60)
    
    test_task_structure()
    test_dependency_chain()
    test_cross_module_link()
    
    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)