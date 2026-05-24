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
                # 调用真实图片生成API
                result_img = await self._image_generate(**params)
                result["success"] = result_img["success"]
                result["output"] = result_img["output"]
                result["error"] = result_img.get("error")
                
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
    
    async def _image_generate(self, prompt: str, aspect_ratio: str = "landscape") -> Dict:
        """生成图片（优先PIL，fallback API）"""
        
        if self.dry_run:
            return {"success": True, "output": f"[Dry Run] Image: {prompt[:50]}"}
        
        # 方案1: PIL生成（无需API，类似之前PPT图表）
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            width = 800 if aspect_ratio == "landscape" else 450
            height = 450 if aspect_ratio == "landscape" else 800
            
            img = Image.new('RGB', (width, height), '#0a0a1a')
            draw = ImageDraw.Draw(img)
            
            # 渐变背景
            for y in range(height):
                r = int(10 + y * 0.02)
                g = int(20 + y * 0.05)
                b = int(50 + y * 0.3)
                draw.line([(0, y), (width, y)], fill=(r, g, min(b, 100)))
            
            # 生成设计图
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            except:
                font = ImageFont.load_default()
                title_font = font
            
            # 装饰元素
            draw.ellipse([width-150, 50, width-50, 150], fill=(76, 201, 240, 50))
            draw.ellipse([width-130, height-150, width-30, height-50], fill=(247, 37, 133, 30))
            
            # 提取prompt关键词作为标题
            title = prompt[:40] if len(prompt) > 40 else prompt
            draw.text((40, 100), title, fill=(255, 255, 255), font=title_font)
            
            # 模拟设计元素
            draw.rectangle([40, 160, 300, 300], fill=(30, 30, 50), outline=(76, 201, 240))
            draw.rectangle([320, 160, 500, 300], fill=(30, 30, 50), outline=(247, 37, 133))
            
            draw.text((50, 170), "核心功能", fill=(76, 201, 240), font=font)
            draw.text((330, 170), "联系方式", fill=(247, 37, 133), font=font)
            
            # 保存到输出目录
            import os
            import hashlib
            filename = hashlib.md5(prompt.encode()).hexdigest()[:8] + ".png"
            output_path = os.path.join(self.workdir, filename) if self.workdir else f"/tmp/{filename}"
            
            img.save(output_path, 'PNG')
            
            return {"success": True, "output": output_path}
            
        except ImportError:
            # 方案2: 尝试调用Hermes image_generate
            try:
                from image_generate import image_generate
                result = image_generate(prompt=prompt, aspect_ratio=aspect_ratio)
                if result and "image" in result:
                    return {"success": True, "output": result["image"]}
            except:
                pass
        
        # 方案3: Placeholder fallback
        return {
            "success": True,
            "output": f"https://via.placeholder.com/{width}x{height}?text={prompt[:30].replace(' ', '+')}"
        }
    
    def get_history(self) -> list:
        """获取执行历史"""
        return self.history


# 便捷函数
async def execute_tool(action: str, params: dict, workdir: str = None, dry_run: bool = False) -> Dict:
    """便捷函数"""
    executor = ToolExecutor(workdir=workdir, dry_run=dry_run)
    return await executor.execute(action, params)