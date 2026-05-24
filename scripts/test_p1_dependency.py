"""
测试P1依赖推断功能
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from execution.agents import Task
from execution.dependency_inferrer import infer_dependencies, DependencyInferrer


def test_file_dependency():
    """测试文件依赖推断"""
    
    tasks = [
        Task(
            id="T1", name="创建配置文件", 
            description="创建config.yaml配置文件，包含数据库连接信息",
            assignee="Developer", priority=5, module="核心"
        ),
        Task(
            id="T2", name="读取配置", 
            description="读取config.yaml文件，解析配置内容",
            assignee="Developer", priority=5, module="核心"
        ),
        Task(
            id="T3", name="数据库连接", 
            description="基于config.yaml建立数据库连接",
            assignee="Developer", priority=4, module="核心"
        ),
    ]
    
    print("\n" + "=" * 50)
    print("测试1: 文件依赖推断")
    print("=" * 50)
    
    print("\n原始任务:")
    for t in tasks:
        print(f"  [{t.id}] {t.name} → {t.assignee}")
        if t.dependencies:
            print(f"       依赖: {t.dependencies}")
    
    tasks = infer_dependencies(tasks)
    
    print("\n推断后依赖:")
    for t in tasks:
        print(f"  [{t.id}] {t.name}")
        if t.dependencies:
            print(f"       推断依赖: {t.dependencies}")
    
    # 验证T2依赖T1
    assert "T1" in tasks[1].dependencies, "T2应该依赖T1（读取依赖创建）"
    # 验证T3依赖T1
    assert "T1" in tasks[2].dependencies, "T3应该依赖T1（基于依赖创建）"
    
    print("\n✓ 文件依赖推断正确")


def test_test_dev_dependency():
    """测试-开发依赖推断"""
    
    tasks = [
        Task(
            id="D1", name="登录功能开发",
            description="实现用户登录功能，包括邮箱验证",
            assignee="Developer", priority=5, module="用户认证"
        ),
        Task(
            id="D2", name="登录页面开发",
            description="开发前端登录页面",
            assignee="Developer", priority=4, module="用户认证"
        ),
        Task(
            id="Q1", name="登录功能测试",
            description="测试登录功能是否正常工作",
            assignee="QA", priority=4, module="用户认证"
        ),
        Task(
            id="Q2", name="集成测试",
            description="集成测试用户认证模块",
            assignee="QA", priority=3, module="用户认证"
        ),
    ]
    
    print("\n" + "=" * 50)
    print("测试2: 测试-开发依赖推断")
    print("=" * 50)
    
    tasks = infer_dependencies(tasks)
    
    print("\n推断结果:")
    for t in tasks:
        print(f"  [{t.id}] {t.name} ({t.assignee})")
        if t.dependencies:
            print(f"       依赖: {t.dependencies}")
    
    # 验证测试任务依赖开发任务
    assert len(tasks[2].dependencies) > 0, "Q1应该有依赖"
    
    print("\n✓ 测试-开发依赖推断正确")


def test_api_dependency():
    """测试API依赖推断"""
    
    tasks = [
        Task(
            id="A1", name="创建API接口",
            description="开发API接口 POST /api/user/login",
            assignee="Developer", priority=5, module="API"
        ),
        Task(
            id="A2", name="前端调用API",
            description="前端调用/api/user/login接口实现登录",
            assignee="Developer", priority=4, module="前端"
        ),
    ]
    
    print("\n" + "=" * 50)
    print("测试3: API依赖推断")
    print("=" * 50)
    
    tasks = infer_dependencies(tasks)
    
    print("\n推断结果:")
    for t in tasks:
        print(f"  [{t.id}] {t.name}")
        if t.dependencies:
            print(f"       依赖: {t.dependencies}")
    
    # 验证A2依赖A1
    assert "A1" in tasks[1].dependencies, "A2应该依赖A1（调用依赖开发）"
    
    print("\n✓ API依赖推断正确")


def test_complex_dependency():
    """测试复杂依赖链"""
    
    tasks = [
        Task(id="M1", name="数据库设计", description="设计用户表结构", assignee="Developer", priority=5, module="核心"),
        Task(id="M2", name="API开发", description="开发用户增删改查API", assignee="Developer", priority=5, module="核心"),
        Task(id="M3", name="前端开发", description="开发用户管理界面", assignee="Developer", priority=4, module="前端"),
        Task(id="M4", name="功能测试", description="测试用户管理功能", assignee="QA", priority=4, module="测试"),
        Task(id="M5", name="系统集成", description="集成用户管理模块到系统", assignee="Developer", priority=3, module="部署"),
    ]
    
    print("\n" + "=" * 50)
    print("测试4: 复杂依赖链")
    print("=" * 50)
    
    tasks = infer_dependencies(tasks)
    
    print("\n推断结果:")
    for t in tasks:
        print(f"  [{t.id}] {t.name} ({t.assignee})")
        if t.dependencies:
            print(f"       依赖: {t.dependencies}")
    
    print("\n✓ 复杂依赖链推断完成")


if __name__ == "__main__":
    print("=" * 50)
    print("P1依赖推断功能测试")
    print("=" * 50)
    
    test_file_dependency()
    test_test_dev_dependency()
    test_api_dependency()
    test_complex_dependency()
    
    print("\n" + "=" * 50)
    print("全部测试通过 ✓")
    print("=" * 50)