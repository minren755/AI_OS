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


class WorkflowEngine:
    """三层编排引擎"""
    
    def __init__(self, tool_executor: Callable = None):
        self.tool_executor = tool_executor or self._default_tool_executor
        
        # 决策层
        self.decision_agents = {
            "CEO": DecisionAgent("CEO", "CEO，负责战略决策和整体方向把控"),
            "CFO": DecisionAgent("CFO", "CFO，关注财务可行性、成本收益分析"),
            "CTO": DecisionAgent("CTO", "CTO，关注技术可行性、实现路径、风险"),
            "CMO": DecisionAgent("CMO", "CMO，关注市场接受度、用户价值、推广策略"),
        }
        
        # 管理层
        self.pm = PMAgent()
        
        # 执行层
        self.execution_agents = {
            "Developer": DeveloperAgent(tool_executor),
            "Designer": DesignerAgent(tool_executor),
            "QA": QAAgent(tool_executor),
            "Operator": OperatorAgent(tool_executor),
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
    
    def _init_llm_configs(self):
        """加载LLM配置"""
        from ..config.settings import get_llm_config
        
        llm_config = get_llm_config()
        if llm_config.get('api_key'):
            for role in ["CEO", "CFO", "CTO", "CMO", "PM", "Developer"]:
                self.llm_configs[role] = llm_config
    
    async def run(self, topic: str) -> Dict:
        """执行完整工作流：讨论 → 拆解 → 执行 → 反馈"""
        
        self._emit("workflow_start", {"topic": topic})
        
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
    
    # ========== Phase 2: 管理层拆解 ==========
    
    async def _run_planning_phase(self, decision: str) -> List[Task]:
        """PM拆解决策为任务"""
        
        prompt = f"""你是PM（产品经理），需要将以下决策拆解为具体可执行的任务。

决策：{decision}

可用Agent及其能力：
- Developer: 写代码、部署、查文档（工具：terminal, write_file, execute_code）
- Designer: UI设计、原型（工具：image_generate, write_file）
- QA: 测试、Bug跟踪（工具：terminal, execute_code）
- Operator: 运营推广、内容发布（工具：send_message, image_generate）

请输出JSON格式任务列表：
[
  {{
    "name": "任务名称",
    "description": "详细描述，包含验收标准",
    "assignee": "Developer",
    "priority": 1-5,
    "dependencies": [],
    "tools_needed": ["terminal", "write_file"]
  }}
]

要求：
1. 每个任务必须只分配给一个Agent
2. 任务之间如果有依赖，填写dependencies（任务名）
3. 按优先级排序
4. 任务描述要具体，包含可执行的细节
"""
        
        raw = await self._call_llm("PM", prompt)
        tasks = self._parse_tasks(raw, decision)
        
        self._emit("tasks_created", {"tasks": [{"name": t.name, "assignee": t.assignee} for t in tasks]})
        
        return tasks
    
    def _parse_tasks(self, raw: str, decision: str) -> List[Task]:
        """解析LLM输出的任务列表"""
        tasks = []
        
        try:
            # 提取JSON
            if "```json" in raw:
                start = raw.find("```json") + 7
                end = raw.find("```", start)
                json_str = raw[start:end].strip()
            elif "[" in raw and "]" in raw:
                start = raw.find("[")
                end = raw.rfind("]") + 1
                json_str = raw[start:end]
            else:
                # 无法解析，生成默认任务
                return self._default_tasks(decision)
            
            parsed = json.loads(json_str)
            
            for i, t in enumerate(parsed):
                task = Task(
                    id=f"task_{i+1}",
                    name=t.get("name", f"任务{i+1}"),
                    description=t.get("description", ""),
                    assignee=t.get("assignee"),
                    priority=t.get("priority", 3),
                    dependencies=t.get("dependencies", []),
                    tools_needed=t.get("tools_needed", [])
                )
                tasks.append(task)
                
        except Exception as e:
            print(f"解析任务失败: {e}")
            tasks = self._default_tasks(decision)
        
        return tasks
    
    def _default_tasks(self, decision: str) -> List[Task]:
        """默认任务（LLM解析失败时使用）"""
        return [
            Task(id="task_1", name="技术方案设计", description=decision,
                 assignee="Developer", priority=5, tools_needed=["terminal", "write_file"]),
            Task(id="task_2", name="UI设计", description="根据功能设计UI",
                 assignee="Designer", priority=4, dependencies=["task_1"],
                 tools_needed=["image_generate", "write_file"]),
            Task(id="task_3", name="功能开发", description="实现功能代码",
                 assignee="Developer", priority=5, dependencies=["task_1", "task_2"],
                 tools_needed=["terminal", "write_file", "execute_code"]),
            Task(id="task_4", name="测试", description="功能测试",
                 assignee="QA", priority=4, dependencies=["task_3"],
                 tools_needed=["terminal", "execute_code"]),
            Task(id="task_5", name="运营推广", description="发布和推广",
                 assignee="Operator", priority=3, dependencies=["task_4"],
                 tools_needed=["send_message", "image_generate"]),
        ]
    
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
    
    async def _default_tool_executor(self, action: str, params: dict) -> ToolResult:
        """默认工具执行器（不执行真实操作，只记录）"""
        self._emit("tool_call", {"action": action, "params": str(params)[:200]})
        return ToolResult(success=True, output=f"[Dry Run] {action}")
    
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
