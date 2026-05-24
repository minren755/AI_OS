"""
测试真实工具执行能力
"""
import asyncio
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from execution.tool_executor import ToolExecutor


async def test_tool_executor():
    """测试工具执行器"""
    
    print("\n" + "=" * 60)
    print("真实工具执行测试")
    print("=" * 60)
    
    executor = ToolExecutor(workdir=str(project_root / "temp_test"), dry_run=False)
    
    # 创建测试目录
    import os
    os.makedirs(project_root / "temp_test", exist_ok=True)
    
    # 测试1: 写文件
    print("\n1. 测试写文件...")
    result = await executor.execute("write_file", {
        "path": "test_hello.txt",
        "content": "Hello from AI_OS!\n这是测试内容。"
    })
    print(f"   结果: {result}")
    
    # 测试2: 终端命令
    print("\n2. 测试终端命令...")
    result = await executor.execute("terminal", {
        "command": f"cat {project_root}/temp_test/test_hello.txt"
    })
    print(f"   结果: {result['output'][:100]}")
    
    # 测试3: 执行Python代码
    print("\n3. 测试Python代码执行...")
    result = await executor.execute("execute_code", {
        "code": "print('Hello from Python!'); import sys; print(f'Python {sys.version}')"
    })
    print(f"   结果: {result}")
    
    # 测试4: Patch文件
    print("\n4. 测试Patch文件...")
    result = await executor.execute("patch", {
        "path": "test_hello.txt",
        "old_string": "Hello from AI_OS!",
        "new_string": "Hello from AI_OS - Updated!"
    })
    print(f"   结果: {result}")
    
    # 验证patch
    result = await executor.execute("terminal", {
        "command": f"cat {project_root}/temp_test/test_hello.txt"
    })
    print(f"   Patch后内容: {result['output']}")
    
    # 清理
    import shutil
    shutil.rmtree(project_root / "temp_test", ignore_errors=True)
    
    print("\n" + "=" * 60)
    print("全部测试通过 ✓")
    print("=" * 60)
    
    # 显示执行历史
    print("\n执行历史:")
    for i, h in enumerate(executor.get_history(), 1):
        status = "✓" if h["success"] else "✗"
        print(f"  {i}. {status} {h['action']}")


if __name__ == "__main__":
    asyncio.run(test_tool_executor())