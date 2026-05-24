"""
完整工作流测试 - "我要做一个公司宣传页"
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from execution.workflow import WorkflowEngine
from execution.agents import Task


async def test_company_page():
    """测试完整工作流：公司宣传页"""
    
    topic = "我要做一个公司宣传页"
    output_dir = project_root / "output" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 70)
    print(f"完整工作流测试: {topic}")
    print(f"输出目录: {output_dir}")
    print("=" * 70)
    
    # 创建工作流引擎
    engine = WorkflowEngine(workdir=str(output_dir), dry_run=False)
    
    # 设置事件回调
    def on_event(event):
        etype = event["type"]
        data = event["data"]
        if etype == "phase":
            print(f"\n[Phase] {data['message']}")
        elif etype == "tasks_created":
            print(f"  → 创建 {data['total_tasks']} 个任务")
        elif etype == "module_tasks_created":
            print(f"  → 模块 [{data['module']}]: {data['tasks']} 个任务")
    
    engine.on_event = on_event
    
    # 执行完整工作流
    print("\n开始执行...\n")
    
    try:
        result = await engine.run(topic)
        
        print("\n" + "=" * 70)
        print("执行结果:")
        print("=" * 70)
        
        print(f"\n决策: {result['决策'][:100]}...")
        
        print(f"\n任务列表 ({len(result['任务'])} 个):")
        for task in result['任务']:
            print(f"  [{task['status']}] {task['name']} → {task['assignee']}")
        
        print(f"\n执行结果:")
        for i, r in enumerate(result['执行结果'], 1):
            print(f"  {i}. {r.get('task', 'Unknown')}")
            if 'output' in r:
                output = r['output']
                if isinstance(output, dict):
                    if 'design_url' in output:
                        print(f"     设计图: {output['design_url']}")
                    if 'prototype_path' in output:
                        print(f"     原型文件: {output['prototype_path']}")
                else:
                    print(f"     结果: {str(output)[:100]}")
        
        # 检查输出文件
        print("\n" + "=" * 70)
        print("生成的文件:")
        print("=" * 70)
        
        for file in output_dir.rglob("*"):
            if file.is_file():
                size = file.stat().st_size
                print(f"  {file.relative_to(output_dir)} ({size} bytes)")
        
        print("\n" + "=" * 70)
        print(f"✓ 工作流完成！输出目录: {output_dir}")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_simplified_workflow():
    """简化测试：跳过决策层，直接从任务开始"""
    
    print("\n" + "=" * 70)
    print("简化工作流测试（跳过决策层）")
    print("=" * 70)
    
    output_dir = project_root / "output" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine = WorkflowEngine(workdir=str(output_dir), dry_run=False)
    
    # 手动创建任务（跳过决策和规划阶段）
    tasks = [
        Task(
            id="DESIGN_1",
            name="设计公司宣传页",
            description="设计现代简约风格的公司宣传页，包含公司Logo、核心业务介绍、联系方式",
            assignee="Designer",
            priority=5,
            module="设计"
        ),
        Task(
            id="DEV_1",
            name="编写宣传页HTML",
            description="编写响应式HTML页面，包含header、main、footer部分",
            assignee="Developer",
            priority=5,
            module="开发",
            dependencies=["DESIGN_1"]
        ),
    ]
    
    print(f"\n任务: {[t.name for t in tasks]}")
    print(f"输出: {output_dir}\n")
    
    # 直接执行
    results = await engine._run_execution_phase(tasks)
    
    print("\n执行结果:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r}")
    
    # 检查输出
    print("\n生成文件:")
    for file in output_dir.rglob("*"):
        if file.is_file():
            print(f"  {file.name} ({file.stat().st_size} bytes)")
            if file.suffix == '.html':
                print(f"\nHTML预览:")
                print(file.read_text()[:500])
    
    print(f"\n✓ 输出目录: {output_dir}")


if __name__ == "__main__":
    # 选择测试模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        asyncio.run(test_simplified_workflow())
    else:
        asyncio.run(test_company_page())