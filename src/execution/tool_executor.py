"""
工具执行器 - 真实工具调用
"""
import asyncio
import subprocess
import json
from typing import Dict, Any, Optional
from pathlib import Path


class ToolExecutor:
    """真实工具执行器"""
    
    def __init__(self, workdir: str = None, dry_run: bool = False):
        self.workdir = workdir or Path.cwd()
        self.dry_run = dry_run
        self.history = []  # 执行历史
    
    async def execute(self, action: str, params: Dict) -> Dict:
        """执行工具调用"""
        
        result = {
            "action": action,
            "params": params,
            "success": False,
            "output": None,
            "error": None
        }
        
        try:
            if action == "terminal":
                output = await self._terminal(**params)
                result["success"] = True
                result["output"] = output
                
            elif action == "write_file":
                output = self._write_file(**params)
                result["success"] = True
                result["output"] = output
                
            elif action == "patch":
                output = self._patch(**params)
                result["success"] = True
                result["output"] = output
                
            elif action == "execute_code":
                output = await self._execute_code(**params)
                result["success"] = True
                result["output"] = output
                
            elif action == "web_search":
                # 简化：返回提示
                result["success"] = True
                result["output"] = f"[Mock] Web search: {params.get('query', '')}"
                
            elif action == "image_generate":
                result["success"] = True
                result["output"] = f"[Mock] Image generated for: {params.get('prompt', '')[:50]}"
                
            else:
                result["error"] = f"Unknown action: {action}"
                
        except Exception as e:
            result["error"] = str(e)
        
        self.history.append(result)
        return result
    
    async def _terminal(self, command: str, timeout: int = 60) -> str:
        """执行终端命令"""
        
        if self.dry_run:
            return f"[Dry Run] {command}"
        
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workdir
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            output = stdout.decode('utf-8', errors='replace')
            if proc.returncode != 0:
                output += f"\n[Exit {proc.returncode}] {stderr.decode('utf-8', errors='replace')}"
            
            return output.strip() or "[No output]"
            
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Command timed out: {command[:50]}")
    
    def _write_file(self, path: str, content: str) -> str:
        """写入文件"""
        
        if self.dry_run:
            return f"[Dry Run] Write {len(content)} chars to {path}"
        
        file_path = Path(self.workdir) / path if not Path(path).is_absolute() else Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content, encoding='utf-8')
        return f"Wrote {len(content)} chars to {file_path}"
    
    def _patch(self, path: str, old_string: str, new_string: str) -> str:
        """修改文件"""
        
        if self.dry_run:
            return f"[Dry Run] Patch {path}"
        
        file_path = Path(self.workdir) / path if not Path(path).is_absolute() else Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = file_path.read_text(encoding='utf-8')
        if old_string not in content:
            raise ValueError(f"Old string not found in {file_path}")
        
        new_content = content.replace(old_string, new_string)
        file_path.write_text(new_content, encoding='utf-8')
        
        return f"Patched {file_path}"
    
    async def _execute_code(self, code: str, language: str = "python") -> str:
        """执行代码"""
        
        if self.dry_run:
            return f"[Dry Run] Execute {language} code ({len(code)} chars)"
        
        if language != "python":
            return f"[Mock] {language} execution not implemented"
        
        # 使用子进程执行Python
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workdir
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        
        output = stdout.decode('utf-8', errors='replace')
        if proc.returncode != 0:
            output += f"\n[Error] {stderr.decode('utf-8', errors='replace')}"
        
        return output.strip() or "[No output]"
    
    def get_history(self) -> list:
        """获取执行历史"""
        return self.history


# 便捷函数
async def execute_tool(action: str, params: dict, workdir: str = None, dry_run: bool = False) -> Dict:
    """便捷函数"""
    executor = ToolExecutor(workdir=workdir, dry_run=dry_run)
    return await executor.execute(action, params)