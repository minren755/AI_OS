"""
AI_OS 执行层架构设计

三层架构：决策层 → 管理层 → 执行层
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable
from enum import Enum
import asyncio


# ============================================
# 基础定义
# ============================================

class AgentType(Enum):
    """Agent类型"""
    # 决策层（讨论型）
    CEO = "CEO"
    CFO = "CFO"
    CTO = "CTO"
    CMO = "CMO"
    
    # 管理层
    PM = "PM"
    
    # 执行层（有工具能力）
    DEVELOPER = "Developer"
    DESIGNER = "Designer"
    QA = "QA"
    OPERATOR = "Operator"
    ANALYST = "Analyst"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """任务定义 - P0增强版"""
    id: str
    name: str
    description: str
    assignee: str = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1  # 1-5, 5最高
    dependencies: List[str] = field(default_factory=list)
    tools_needed: List[str] = field(default_factory=list)
    # P0新增字段
    acceptance_criteria: List[str] = field(default_factory=list)  # 验收标准
    estimated_steps: int = 3  # 预计步骤数
    context_files: List[str] = field(default_factory=list)  # 需要读取的文件
    module: str = ""  # 所属模块
    result: Any = None
    error: str = None


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: str = None


# ============================================
# Agent基类
# ============================================

class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, tools: List[str] = None):
        self.name = name
        self.tools = tools or []
        self.task_history: List[Task] = []
    
    @abstractmethod
    async def execute(self, task: Task) -> Task:
        """执行任务"""
        pass
    
    def can_handle(self, task: Task) -> bool:
        """判断是否能处理该任务"""
        # 检查工具是否匹配
        for tool in task.tools_needed:
            if tool not in self.tools:
                return False
        return True


# ============================================
# 决策层（现有）
# ============================================

class DecisionAgent(BaseAgent):
    """决策层Agent - 讨论型，无工具"""
    
    def __init__(self, name: str, role_desc: str):
        super().__init__(name, tools=[])  # 决策层无工具
        self.role_desc = role_desc
        self.satisfied = False
        self.last_response: str = None
    
    async def execute(self, task: Task) -> Task:
        """决策层不执行具体任务，只参与讨论"""
        # 这里复用现有DiscussionEngine
        task.status = TaskStatus.COMPLETED
        task.result = self.last_response
        return task


# ============================================
# 管理层 - PM
# ============================================

class PMAgent(BaseAgent):
    """PM - 产品经理，拆解任务、派发执行"""
    
    def __init__(self):
        super().__init__("PM", tools=["write_file", "patch", "todo"])
        self.pending_tasks: List[Task] = []
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent):
        """注册执行Agent"""
        self.agents[agent.name] = agent
    
    async def plan_from_decision(self, decision: str) -> List[Task]:
        """从决策生成任务列表"""
        # 这里调用LLM解析决策，生成任务
        prompt = f"""
你是PM，需要将以下决策拆解为具体任务：

决策：{decision}

请输出JSON格式的任务列表：
[
  {{
    "name": "任务名称",
    "description": "详细描述",
    "assignee": "Developer/Designer/QA/Operator",
    "priority": 1-5,
    "tools_needed": ["terminal", "write_file"]
  }}
]
"""
        # 调用LLM获取任务列表
        # ... 省略LLM调用代码
        tasks = []
        return tasks
    
    def find_best_agent(self, task: Task) -> str:
        """找到最适合的Agent"""
        for name, agent in self.agents.items():
            if agent.can_handle(task):
                return name
        return None
    
    async def execute(self, task: Task) -> Task:
        """PM执行：拆解决策→派发任务→收集结果"""
        # 1. 拆解决策
        sub_tasks = await self.plan_from_decision(task.description)
        
        # 2. 派发任务
        results = []
        for sub_task in sub_tasks:
            assignee = self.find_best_agent(sub_task)
            if assignee:
                sub_task.assignee = assignee
                sub_task.status = TaskStatus.ASSIGNED
                # 执行任务
                agent = self.agents[assignee]
                result = await agent.execute(sub_task)
                results.append(result)
        
        # 3. 汇总结果
        task.result = results
        task.status = TaskStatus.COMPLETED
        return task


# ============================================
# 执行层 - Developer
# ============================================

class DeveloperAgent(BaseAgent):
    """Developer - 写代码、部署"""
    
    def __init__(self, tool_executor: Callable = None):
        super().__init__("Developer", tools=[
            "terminal",      # 执行命令
            "write_file",    # 写代码
            "patch",         # 修改代码
            "execute_code",  # 运行Python
            "web_search"     # 查文档
        ])
        self.tool_executor = tool_executor  # 工具执行器（注入）
    
    async def execute(self, task: Task) -> Task:
        """执行开发任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            # 1. 分析任务，生成执行计划
            plan = await self._plan_task(task)
            
            # 2. 逐步执行
            results = []
            for step in plan:
                result = await self._execute_step(step)
                results.append(result)
                
                if not result.success:
                    task.status = TaskStatus.FAILED
                    task.error = f"Step failed: {step['action']}"
                    return task
            
            # 3. 验证结果
            verification = await self._verify_task(task)
            
            if verification.success:
                task.status = TaskStatus.COMPLETED
                task.result = results
            else:
                task.status = TaskStatus.FAILED
                task.error = verification.error
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        return task
    
    async def _plan_task(self, task: Task) -> List[Dict]:
        """生成执行计划"""
        prompt = f"""
你是Developer，需要完成以下任务：

任务：{task.name}
描述：{task.description}

请输出执行步骤JSON：
[
  {{"action": "terminal", "params": {{"command": "npm init -y"}}}},
  {{"action": "write_file", "params": {{"path": "app.js", "content": "..."}}}},
  {{"action": "terminal", "params": {{"command": "node app.js"}}}}
]
"""
        # 调用LLM获取计划
        # 返回示例
        return [
            {"action": "write_file", "params": {"path": f"{task.id}_app.js", "content": "console.log('Hello AI_OS!')"}},
            {"action": "terminal", "params": {"command": f"echo 'Task {task.id} completed'"}}
        ]
    
    async def _execute_step(self, step: Dict) -> ToolResult:
        """执行单个步骤"""
        action = step.get("action")
        params = step.get("params", {})
        
        if self.tool_executor:
            return await self.tool_executor(action, params)
        
        return ToolResult(success=True, output=f"Mock: {action}")
    
    async def _verify_task(self, task: Task) -> ToolResult:
        """验证任务完成"""
        # 运行测试、检查文件等
        return ToolResult(success=True, output="Verified")


# ============================================
# 执行层 - Designer
# ============================================

class DesignerAgent(BaseAgent):
    """Designer - UI设计、原型"""
    
    def __init__(self, tool_executor: Callable = None):
        super().__init__("Designer", tools=[
            "image_generate",  # 生成设计图
            "write_file",     # 输出HTML原型
            "vision_analyze"  # 审视设计
        ])
        self.tool_executor = tool_executor
    
    async def execute(self, task: Task) -> Task:
        """执行设计任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            # 1. 生成设计稿
            design = await self._generate_design(task)
            
            # 2. 输出原型
            prototype = await self._create_prototype(task, design)
            
            task.result = {
                "design_url": design.output,
                "prototype_path": prototype.output
            }
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        return task
    
    async def _generate_design(self, task: Task) -> ToolResult:
        """生成设计"""
        prompt = f"UI设计：{task.description}，现代简约风格"
        
        if self.tool_executor:
            return await self.tool_executor("image_generate", {
                "prompt": prompt,
                "aspect_ratio": "landscape"
            })
        
        return ToolResult(success=True, output="https://mock-design-url.com/image.png")
    
    async def _create_prototype(self, task: Task, design: ToolResult) -> ToolResult:
        """创建原型HTML"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{task.name}</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        h1 {{ color: #4cc9f0; }}
        img {{ max-width: 100%; }}
    </style>
</head>
<body>
    <header>
        <h1>公司宣传页</h1>
        <p>现代简约风格设计</p>
    </header>
    <main>
        <img src="{design.output}" alt="设计稿">
        <h2>核心业务</h2>
        <p>专业AI解决方案提供商</p>
        <h2>联系方式</h2>
        <p>Email: contact@company.com</p>
    </main>
    <footer>
        <p>© 2026 AI创世者</p>
    </footer>
</body>
</html>
"""
        
        if self.tool_executor:
            return await self.tool_executor("write_file", {
                "path": f"{task.id}_prototype.html",  # 相对路径，由workdir决定
                "content": html_content
            })
        
        return ToolResult(success=True, output=f"/tmp/{task.id}.html")


# ============================================
# 执行层 - QA
# ============================================

class QAAgent(BaseAgent):
    """QA - 测试"""
    
    def __init__(self, tool_executor: Callable = None):
        super().__init__("QA", tools=[
            "terminal",      # 运行测试
            "execute_code",  # 自动化测试
            "patch"          # 提交Bug修复
        ])
        self.tool_executor = tool_executor
    
    async def execute(self, task: Task) -> Task:
        """执行测试任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            # 1. 编写测试用例
            test_cases = await self._write_test_cases(task)
            
            # 2. 执行测试
            test_results = await self._run_tests(test_cases)
            
            # 3. 生成报告
            task.result = {
                "test_cases": test_cases,
                "results": test_results,
                "pass_rate": sum(1 for r in test_results if r.success) / len(test_results)
            }
            
            if task.result["pass_rate"] >= 0.8:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Pass rate too low: {task.result['pass_rate']}"
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        return task
    
    async def _write_test_cases(self, task: Task) -> List[Dict]:
        """编写测试用例"""
        return [
            {"name": "test_login", "type": "unit"},
            {"name": "test_ui", "type": "e2e"}
        ]
    
    async def _run_tests(self, test_cases: List[Dict]) -> List[ToolResult]:
        """执行测试"""
        results = []
        for tc in test_cases:
            # 模拟测试执行
            results.append(ToolResult(success=True, output=f"{tc['name']} passed"))
        return results


# ============================================
# 执行层 - Operator
# ============================================

class OperatorAgent(BaseAgent):
    """Operator - 运营"""
    
    def __init__(self, tool_executor: Callable = None):
        super().__init__("Operator", tools=[
            "send_message",   # 发送内容
            "image_generate", # 内容配图
            "web_search"      # 市场调研
        ])
        self.tool_executor = tool_executor
    
    async def execute(self, task: Task) -> Task:
        """执行运营任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            # 1. 生成内容
            content = await self._create_content(task)
            
            # 2. 生成配图
            image = await self._create_image(task, content)
            
            # 3. 发布
            publish_result = await self._publish(task, content, image)
            
            task.result = {
                "content": content,
                "image_url": image.output,
                "publish_status": publish_result.output
            }
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        return task
    
    async def _create_content(self, task: Task) -> str:
        """生成运营内容"""
        return f"关于{task.name}的运营内容..."
    
    async def _create_image(self, task: Task, content: str) -> ToolResult:
        """生成配图"""
        if self.tool_executor:
            return await self.tool_executor("image_generate", {
                "prompt": f"营销图：{content[:50]}",
                "aspect_ratio": "square"
            })
        return ToolResult(success=True, output="https://mock-image.com/promo.png")
    
    async def _publish(self, task: Task, content: str, image: ToolResult) -> ToolResult:
        """发布内容"""
        if self.tool_executor:
            return await self.tool_executor("send_message", {
                "target": "wechat",
                "message": f"{content}\n\nMEDIA:{image.output}"
            })
        return ToolResult(success=True, output="Published to WeChat")


# ============================================
# 任务调度器
# ============================================

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
    
    def register(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.name] = agent
    
    def submit(self, task: Task):
        """提交任务"""
        self.task_queue.append(task)
    
    def find_agent(self, task: Task) -> BaseAgent:
        """找到能处理任务的Agent"""
        for agent in self.agents.values():
            if agent.can_handle(task):
                return agent
        return None
    
    async def run(self):
        """运行调度"""
        while self.task_queue:
            task = self.task_queue.pop(0)
            
            # 检查依赖
            if not self._check_dependencies(task):
                # 依赖未完成，放回队列末尾
                self.task_queue.append(task)
                continue
            
            # 找Agent
            agent = self.find_agent(task)
            if not agent:
                task.status = TaskStatus.BLOCKED
                task.error = "No available agent"
                continue
            
            # 执行
            task.assignee = agent.name
            result = await agent.execute(task)
            
            if result.status == TaskStatus.COMPLETED:
                self.completed_tasks.append(result)
            else:
                # 失败任务处理
                print(f"Task {task.id} failed: {task.error}")
    
    def _check_dependencies(self, task: Task) -> bool:
        """检查依赖是否完成"""
        for dep_id in task.dependencies:
            if not any(t.id == dep_id and t.status == TaskStatus.COMPLETED 
                      for t in self.completed_tasks):
                return False
        return True


# ============================================
# 工作流示例
# ============================================

async def example_workflow():
    """示例：创业功能开发"""
    
    # 1. 创建调度器
    scheduler = TaskScheduler()
    
    # 2. 注册Agent（需要注入真实的工具执行器）
    # 这里用mock演示
    async def mock_executor(action: str, params: dict) -> ToolResult:
        return ToolResult(success=True, output=f"Mock {action}")
    
    scheduler.register(PMAgent())
    scheduler.register(DeveloperAgent(mock_executor))
    scheduler.register(DesignerAgent(mock_executor))
    scheduler.register(QAAgent(mock_executor))
    scheduler.register(OperatorAgent(mock_executor))
    
    # PM需要知道有哪些执行Agent
    for name, agent in scheduler.agents.items():
        if name != "PM":
            scheduler.agents["PM"].register_agent(agent)
    
    # 3. 决策层讨论结果（模拟）
    decision = """
    决策：开发用户登录功能
    - 用OAuth2.0
    - 支持微信/支付宝登录
    - 预算：5万
    - 周期：2周
    """
    
    # 4. PM拆解任务
    tasks = await scheduler.agents["PM"].plan_from_decision(decision)
    
    # 5. 提交任务
    for task in tasks:
        scheduler.submit(task)
    
    # 6. 执行
    await scheduler.run()
    
    # 7. 结果
    print(f"完成 {len(scheduler.completed_tasks)} 个任务")
    for task in scheduler.completed_tasks:
        print(f"  - {task.name}: {task.status.value}")


if __name__ == "__main__":
    asyncio.run(example_workflow())
