"""
测试P1依赖推断 - 真实场景演示
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from execution.agents import Task
from execution.dependency_inferrer import infer_dependencies


def demo_p1_inference():
    """演示P1依赖推断效果"""
    
    print("\n" + "=" * 60)
    print("P1依赖推断演示 - 真实开发场景")
    print("=" * 60)
    
    # 模拟一个真实的登录功能开发任务列表（LLM可能输出）
    tasks = [
        Task(
            id="AUTH_1",
            name="创建用户表",
            description="创建users数据表，包含id、email、password_hash字段",
            assignee="Developer",
            priority=5,
            module="用户认证"
        ),
        Task(
            id="AUTH_2",
            name="开发登录API",
            description="开发POST /api/auth/login接口，验证用户凭证",
            assignee="Developer",
            priority=5,
            module="用户认证"
        ),
        Task(
            id="AUTH_3",
            name="创建配置文件",
            description="创建config.yaml，配置JWT密钥和过期时间",
            assignee="Developer",
            priority=4,
            module="用户认证"
        ),
        Task(
            id="AUTH_4",
            name="读取配置",
            description="读取config.yaml配置，初始化JWT验证模块",
            assignee="Developer",
            priority=4,
            module="用户认证"
        ),
        Task(
            id="AUTH_5",
            name="前端登录页面",
            description="开发登录页面，调用/api/auth/login接口",
            assignee="Developer",
            priority=4,
            module="用户认证"
        ),
        Task(
            id="AUTH_6",
            name="登录功能测试",
            description="测试登录功能完整流程",
            assignee="QA",
            priority=4,
            module="用户认证"
        ),
    ]
    
    print("\n原始任务（无依赖）:")
    print("-" * 60)
    for t in tasks:
        print(f"  [{t.id}] {t.name}")
        print(f"       描述: {t.description[:40]}...")
        print(f"       执行者: {t.assignee}")
        print()
    
    # 应用P1依赖推断
    tasks = infer_dependencies(tasks)
    
    print("\n推断后依赖关系:")
    print("-" * 60)
    for t in tasks:
        print(f"  [{t.id}] {t.name} ({t.assignee})")
        if t.dependencies:
            deps_desc = ", ".join(t.dependencies)
            print(f"       └─ 依赖: {deps_desc}")
        print()
    
    # 统计推断结果
    inferred_count = sum(1 for t in tasks if t.dependencies)
    print("-" * 60)
    print(f"推断结果: {inferred_count}/{len(tasks)} 个任务有依赖")
    
    # 显示依赖链
    print("\n依赖链分析:")
    print("-" * 60)
    
    # 按拓扑排序显示
    completed = set()
    remaining = list(tasks)
    level = 0
    
    while remaining:
        ready = [t for t in remaining if all(d in completed for d in t.dependencies)]
        if not ready:
            break
        level_tasks = []
        for t in ready:
            level_tasks.append(t.id)
            completed.add(t.id)
            remaining.remove(t)
        
        if level_tasks:
            level += 1
            print(f"  Level {level}: {', '.join(level_tasks)}")
    
    print("\n" + "=" * 60)
    print("P1依赖推断效果:")
    print("  - 自动识别文件依赖（AUTH_4 → AUTH_3）")
    print("  - 自动识别测试依赖（AUTH_6 → AUTH_2, AUTH_5）")
    print("  - 无需LLM手动填写dependencies")
    print("=" * 60)


if __name__ == "__main__":
    demo_p1_inference()