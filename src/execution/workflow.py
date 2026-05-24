"""
AI_OS 三层编排引擎

决策层讨论 → 管理层拆解 → 执行层干活 → 结果反馈
"""
import json
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

import httpx
import yaml

from execution.agents import (
    BaseAgent, DecisionAgent, PMAgent, DeveloperAgent,
    DesignerAgent, QAAgent, OperatorAgent,
    Task, TaskStatus, ToolResult
)
from execution.dependency_inferrer import infer_dependencies
from execution.tool_executor import ToolExecutor
from execution.info_checker import check_and_ask


class WorkflowEngine:
    """三层编排引擎"""
    
    def __init__(self, workdir: str = None, dry_run: bool = False, tool_executor: Callable = None):
        # 工具执行器
        self.executor = ToolExecutor(workdir=workdir, dry_run=dry_run)
        
        # 适配器：将ToolExecutor包装成Agent需要的格式
        async def tool_adapter(action: str, params: dict) -> ToolResult:
            result = await self.executor.execute(action, params)
            return ToolResult(
                success=result["success"],
                output=result["output"],
                error=result["error"]
            )
        
        self.tool_executor = tool_executor or tool_adapter
        
        # 决策层
        self.decision_agents = {
            "CEO": DecisionAgent("CEO", "CEO，负责战略决策和整体方向把控"),
            "CFO": DecisionAgent("CFO", "CFO，关注财务可行性、成本收益分析"),
            "CTO": DecisionAgent("CTO", "CTO，关注技术可行性、实现路径、风险"),
            "CMO": DecisionAgent("CMO", "CMO，关注市场接受度、用户价值、推广策略"),
        }
        
        # 管理层
        self.pm = PMAgent()
        
        # 执行层（注入真实工具执行器）
        self.execution_agents = {
            "Developer": DeveloperAgent(self.tool_executor),
            "Designer": DesignerAgent(self.tool_executor),
            "QA": QAAgent(self.tool_executor),
            "Operator": OperatorAgent(self.tool_executor),
        }
        
        # PM注册执行Agent
        for agent in self.execution_agents.values():
            self.pm.register_agent(agent)
        
        # LLM配置
        self.llm_configs: Dict[str, Dict] = {}
        self._init_llm_configs()
        
        # 工作流状态
        self.workflow_log: List[Dict] = []
        self.on_event: Callable = None
        self.workdir = workdir
        self.dry_run = dry_run
        
        # 交互状态（方案B）
        self.waiting_for_input: bool = False
        self.pending_questions: List[str] = []
        self.user_responses: List[str] = []
        self.original_topic: str = ""
    
    def _init_llm_configs(self):
        """加载LLM配置"""
        from config.settings import get_llm_config
        
        llm_config = get_llm_config()
        if llm_config.get('api_key'):
            for role in ["CEO", "CFO", "CTO", "CMO", "PM", "Developer"]:
                self.llm_configs[role] = llm_config
    
    async def run(self, topic: str) -> Dict:
        """执行完整工作流：讨论 → 拆解 → 执行 → 反馈"""
        
        self._emit("workflow_start", {"topic": topic})
        
        # ===== 方案B：信息完整性检查 =====
        info_check = check_and_ask(topic)
        if info_check["need_input"]:
            self.waiting_for_input = True
            self.original_topic = topic
            self.pending_questions = info_check["questions"]
            
            self._emit("need_input", {
                "questions": info_check["questions"],
                "prompt": info_check["prompt"],
                "missing": info_check["missing"]
            })
            
            return {
                "状态": "等待用户输入",
                "问题": info_check["questions"],
                "提示": info_check["prompt"]
            }
        
        # ========== Phase 1: 决策层讨论 ==========
        self._emit("phase", {"phase": "decision", "message": "决策层讨论中..."})
        decision = await self._run_decision_phase(topic)
        
        # ========== Phase 2: 管理层拆解 ==========
        self._emit("phase", {"phase": "planning", "message": "PM拆解任务中..."})
        tasks = await self._run_planning_phase(decision)
        
        # ========== Phase 3: 执行层工作 ==========
        self._emit("phase", {"phase": "execution", "message": "执行层工作中..."})
        results = await self._run_execution_phase(tasks)
        
        # ========== Phase 4: 反馈层 ==========
        self._emit("phase", {"phase": "feedback", "message": "汇总结果..."})
        feedback = await self._run_feedback_phase(decision, results)
        
        # 保存工作流日志
        self._save_workflow_log(topic, decision, tasks, results, feedback)
        
        self._emit("workflow_end", {"feedback": feedback})
        
        return {
            "议题": topic,
            "决策": decision,
            "任务": [{"name": t.name, "assignee": t.assignee, "status": t.status.value} for t in tasks],
            "执行结果": results,
            "反馈": feedback
        }
    
    async def continue_with_input(self, user_input: str) -> Dict:
        """
        用户输入后继续执行（方案B）
        
        Args:
            user_input: 用户的回答，可以是单个字符串或多个问题的回答
        """
        if not self.waiting_for_input:
            return {"错误": "当前不在等待输入状态"}
        
        # 记录用户回答
        self.user_responses.append(user_input)
        
        # 合并原始主题和用户补充信息
        enhanced_topic = self.original_topic
        if user_input.strip() and user_input != "继续":
            enhanced_topic += f"\n\n用户补充信息：{user_input}"
        
        # 重置状态
        self.waiting_for_input = False
        self._emit("input_received", {"input": user_input})
        
        # 继续执行工作流
        return await self.run(enhanced_topic)
    
    # ========== Phase 1: 决策层讨论 ==========
    
    async def _run_decision_phase(self, topic: str) -> str:
        """决策层讨论（复用DiscussionEngine）"""
        from discussion.engine import DiscussionEngine, DiscussionConfig
        
        config = DiscussionConfig(max_rounds=3)
        engine = DiscussionEngine(config)
        engine.on_event = lambda e: self._emit("decision", e)
        
        result = await engine.run(topic)
        
        # 提取CEO总结作为决策
        decision = result.get("观点汇总", [{}])[-1].get("content", topic)
        
        self._emit("decision_result", {"decision": decision})
        
        return decision
    
    # ========== Phase 2: 管理层拆解（P0两阶段拆解）==========
    
    async def _run_planning_phase(self, decision: str) -> List[Task]:
        """PM两阶段拆解：先拆模块，再拆任务"""
        
        self._emit("planning_start", {"decision": decision})
        
        # ===== Phase 2.1: 拆大模块（做什么）=====
        modules = await self._plan_modules(decision)
        self._emit("modules_created", {"modules": modules})
        
        # ===== Phase 2.2: 每模块拆子任务（怎么做）=====
        all_tasks = []
        for module in modules:
            tasks = await self._plan_module_tasks(module, decision)
            all_tasks.extend(tasks)
            self._emit("module_tasks_created", {"module": module["name"], "tasks": len(tasks)})
        
        # 建立跨模块依赖关系
        all_tasks = self._link_cross_module_deps(all_tasks, modules)
        
        # 按优先级排序
        all_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        self._emit("tasks_created", {"total_tasks": len(all_tasks)})
        
        return all_tasks
    
    async def _plan_modules(self, decision: str) -> List[Dict]:
        """Phase 2.1: 拆大模块"""
        
        prompt = f"""你是资深PM，需要将以下决策拆解为功能模块。

决策：{decision}

请输出JSON格式模块列表：
[
  {{
    "name": "模块名称",
    "description": "模块功能概述",
    "priority": 1-5,
    "estimated_tasks": 3
  }}
]

要求：
1. 模块粒度适中（每个模块3-5个任务）
2. 模块之间相对独立，减少依赖
3. 按实现优先级排序
4. 只输出JSON，不要解释
"""
        
        raw = await self._call_llm("PM", prompt)
        modules = self._parse_modules(raw)
        
        if not modules:
            # fallback默认模块
            modules = [
                {"name": "核心功能", "description": "实现核心业务逻辑", "priority": 5, "estimated_tasks": 3},
                {"name": "用户界面", "description": "前端展示和交互", "priority": 4, "estimated_tasks": 2},
                {"name": "测试验证", "description": "功能测试和质量保证", "priority": 3, "estimated_tasks": 2},
            ]
        
        return modules
    
    async def _plan_module_tasks(self, module: Dict, decision: str) -> List[Task]:
        """Phase 2.2: 每个模块拆具体任务"""
        
        prompt = f"""你是资深PM，需要将以下模块拆解为具体可执行的任务。

模块：{module['name']}
模块描述：{module['description']}
整体决策：{decision}

可用Agent及其能力：
- Developer: 写代码、部署、查文档（工具：terminal, write_file, execute_code）
- Designer: UI设计、原型（工具：image_generate, write_file）
- QA: 测试、Bug跟踪（工具：terminal, execute_code）
- Operator: 运营推广、内容发布（工具：send_message, image_generate）

请输出JSON格式任务列表：
[
  {{
    "name": "任务名称",
    "description": "详细描述",
    "acceptance_criteria": ["验收条件1", "验收条件2"],
    "assignee": "Developer",
    "priority": 1-5,
    "estimated_steps": 3,
    "tools_needed": ["terminal", "write_file"],
    "context_files": ["可能需要的文件路径"]
  }}
]

要求：
1. 每个任务有明确的验收标准（可测试）
2. estimated_steps表示预计执行步骤数
3. context_files列出可能需要的上下文文件
4. 优先级继承模块优先级
5. 只输出JSON，不要解释
"""
        
        raw = await self._call_llm("PM", prompt)
        tasks = self._parse_module_tasks(raw, module)
        
        if not tasks:
            # fallback默认任务
            tasks = self._default_module_tasks(module)
        
        # P1: 智能依赖推断
        tasks = infer_dependencies(tasks)
        
        return tasks
    
    def _parse_modules(self, raw: str) -> List[Dict]:
        """解析模块列表"""
        try:
            if "```json" in raw:
                start = raw.find("```json") + 7
                end = raw.find("```", start)
                json_str = raw[start:end].strip()
            elif "[" in raw and "]" in raw:
                start = raw.find("[")
                end = raw.rfind("]") + 1
                json_str = raw[start:end]
            else:
                return []
            
            return json.loads(json_str)
        except:
            return []
    
    def _parse_module_tasks(self, raw: str, module: Dict) -> List[Task]:
        """解析模块任务列表（P0增强版）"""
        tasks = []
        
        try:
            if "```json" in raw:
                start = raw.find("```json") + 7
                end = raw.find("```", start)
                json_str = raw[start:end].strip()
            elif "[" in raw and "]" in raw:
                start = raw.find("[")
                end = raw.rfind("]") + 1
                json_str = raw[start:end]
            else:
                return []
            
            parsed = json.loads(json_str)
            
            module_prefix = module["name"][:4].upper()
            
            for i, t in enumerate(parsed):
                task = Task(
                    id=f"{module_prefix}_{i+1}",
                    name=t.get("name", f"任务{i+1}"),
                    description=t.get("description", ""),
                    assignee=t.get("assignee"),
                    priority=t.get("priority", module.get("priority", 3)),
                    dependencies=[],  # 模块内依赖在后面处理
                    tools_needed=t.get("tools_needed", []),
                    acceptance_criteria=t.get("acceptance_criteria", []),
                    estimated_steps=t.get("estimated_steps", 3),
                    context_files=t.get("context_files", []),
                    module=module["name"]
                )
                tasks.append(task)
            
            # 模块内按顺序建立依赖
            for i in range(1, len(tasks)):
                if tasks[i].assignee != tasks[i-1].assignee or tasks[i].priority > tasks[i-1].priority:
                    # 不同Agent或高优先级任务，依赖前一个
                    tasks[i].dependencies.append(tasks[i-1].id)
                
        except Exception as e:
            print(f"解析任务失败: {e}")
            tasks = self._default_module_tasks(module)
        
        return tasks
    
    def _default_module_tasks(self, module: Dict) -> List[Task]:
        """模块默认任务"""
        module_prefix = module["name"][:4].upper()
        return [
            Task(id=f"{module_prefix}_1", name="设计方案", description=module["description"],
                 assignee="Developer", priority=module.get("priority", 3), 
                 acceptance_criteria=["方案文档完成"], module=module["name"],
                 tools_needed=["terminal", "write_file"]),
            Task(id=f"{module_prefix}_2", name="实现功能", description="代码实现",
                 assignee="Developer", priority=module.get("priority", 3), 
                 dependencies=[f"{module_prefix}_1"],
                 acceptance_criteria=["功能可用"], module=module["name"],
                 tools_needed=["terminal", "write_file", "execute_code"]),
            Task(id=f"{module_prefix}_3", name="验证测试", description="功能验证",
                 assignee="QA", priority=module.get("priority", 3)-1, 
                 dependencies=[f"{module_prefix}_2"],
                 acceptance_criteria=["测试通过"], module=module["name"],
                 tools_needed=["terminal", "execute_code"]),
        ]
    
    def _link_cross_module_deps(self, all_tasks: List[Task], modules: List[Dict]) -> List[Task]:
        """建立跨模块依赖关系"""
        # 按模块优先级建立依赖链
        module_order = [m["name"] for m in sorted(modules, key=lambda m: m["priority"], reverse=True)]
        
        # 找每个模块的第一个任务
        module_first_tasks = {}
        for task in all_tasks:
            if task.module not in module_first_tasks:
                module_first_tasks[task.module] = task
        
        # 高优先级模块完成后，低优先级模块才能开始
        for i in range(1, len(module_order)):
            prev_module = module_order[i-1]
            curr_module = module_order[i]
            
            prev_tasks = [t for t in all_tasks if t.module == prev_module]
            curr_first = module_first_tasks.get(curr_module)
            
            if prev_tasks and curr_first:
                # 当前模块第一个任务依赖前一模块最后一个任务
                last_prev = prev_tasks[-1]
                curr_first.dependencies.append(last_prev.id)
        
        return all_tasks
    
    # ========== Phase 3: 执行层工作 ==========
    
    async def _run_execution_phase(self, tasks: List[Task]) -> List[Dict]:
        """执行层按依赖顺序工作"""
        results = []
        completed_ids = set()
        max_iterations = len(tasks) * 2  # 防止死循环
        iteration = 0
        
        while tasks and iteration < max_iterations:
            iteration += 1
            
            # 找到可执行的任务（依赖已满足）
            ready = [t for t in tasks if self._deps_satisfied(t, completed_ids)]
            
            if not ready:
                # 检查是否有循环依赖
                if tasks:
                    print(f"⚠️ 剩余任务可能有循环依赖: {[t.name for t in tasks]}")
                    break
                break
            
            # 按优先级排序
            ready.sort(key=lambda t: t.priority, reverse=True)
            
            # 执行可并行的任务（无相互依赖的）
            parallel_tasks = self._find_parallel_tasks(ready)
            
            if len(parallel_tasks) > 1:
                # 并行执行
                coros = [self._execute_single_task(t) for t in parallel_tasks]
                task_results = await asyncio.gather(*coros, return_exceptions=True)
                
                for t, r in zip(parallel_tasks, task_results):
                    if isinstance(r, Exception):
                        t.status = TaskStatus.FAILED
                        t.error = str(r)
                    else:
                        completed_ids.add(t.id)
                    results.append(self._task_to_dict(t))
                    tasks.remove(t)
            else:
                # 串行执行
                task = ready[0]
                await self._execute_single_task(task)
                
                if task.status == TaskStatus.COMPLETED:
                    completed_ids.add(task.id)
                
                results.append(self._task_to_dict(task))
                tasks.remove(task)
        
        return results
    
    def _find_parallel_tasks(self, ready: List[Task]) -> List[Task]:
        """找到可并行执行的任务（不同Agent、无相互依赖）"""
        parallel = []
        used_agents = set()
        
        for task in ready:
            if task.assignee not in used_agents:
                parallel.append(task)
                used_agents.add(task.assignee)
        
        return parallel
    
    async def _execute_single_task(self, task: Task) -> Task:
        """执行单个任务"""
        self._emit("task_start", {"task": task.name, "assignee": task.assignee})
        
        agent = self.execution_agents.get(task.assignee)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"Agent {task.assignee} not found"
            return task
        
        try:
            result = await agent.execute(task)
            self._emit("task_done", {
                "task": task.name, 
                "assignee": task.assignee,
                "status": task.status.value,
                "result": task.result
            })
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._emit("task_failed", {"task": task.name, "error": str(e)})
        
        return task
    
    def _deps_satisfied(self, task: Task, completed_ids: set) -> bool:
        """检查依赖是否满足"""
        return all(dep in completed_ids for dep in task.dependencies)
    
    # ========== Phase 4: 反馈层 ==========
    
    async def _run_feedback_phase(self, decision: str, results: List[Dict]) -> str:
        """反馈：CEO审查执行结果"""
        
        prompt = f"""你是CEO，审查以下执行结果：

决策：{decision}

执行结果：
{json.dumps(results, ensure_ascii=False, indent=2)}

请给出：
1. 执行结果是否满足决策要求？
2. 有哪些风险或需要改进的地方？
3. 下一步建议？

200字以内。"""
        
        feedback = await self._call_llm("CEO", prompt)
        
        self._emit("feedback", {"content": feedback})
        
        return feedback
    
    # ========== 工具方法 ==========
    
    async def _call_llm(self, agent: str, prompt: str) -> str:
        """调用LLM"""
        cfg = self.llm_configs.get(agent)
        if not cfg:
            return "配置缺失"
        
        url = cfg['base_url'].rstrip('/') + '/chat/completions'
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": cfg['model'],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return ""
    
    def _emit(self, event_type: str, data: Dict):
        """发送事件"""
        event = {
            "type": event_type,
            "data": data,
            "time": datetime.now().strftime("%H:%M:%S")
        }
        self.workflow_log.append(event)
        
        if self.on_event and callable(self.on_event):
            self.on_event(event)
    
    def _task_to_dict(self, task: Task) -> Dict:
        """Task转字典"""
        return {
            "id": task.id,
            "name": task.name,
            "assignee": task.assignee,
            "status": task.status.value,
            "result": str(task.result)[:500] if task.result else None,
            "error": task.error
        }
    
    def _save_workflow_log(self, topic, decision, tasks, results, feedback):
        """保存工作流日志"""
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(log_file, "w") as f:
            json.dump({
                "topic": topic,
                "decision": decision,
                "tasks": [self._task_to_dict(t) for t in tasks],
                "results": results,
                "feedback": feedback,
                "events": self.workflow_log,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📄 工作流日志: {log_file}")


async def test_workflow():
    """测试完整工作流"""
    engine = WorkflowEngine()
    
    result = await engine.run("开发一个AI简历优化小程序")
    print("\n" + "=" * 50)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(test_workflow())
