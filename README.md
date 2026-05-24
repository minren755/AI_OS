# AI_OS - 企业级多Agent协作操作系统

让多个AI Agent像真实团队一样协作：讨论决策、拆解任务、执行交付。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        用户输入议题                           │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   决策层 (Decision Layer)                    │
│  ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐            │
│  │ CEO │──▶│ CFO │──▶│ CTO │──▶│ CMO │──▶│ CSO │──┐        │
│  └─────┘   └─────┘   └─────┘   └─────┘   └─────┘  │        │
│      ▲                                               │        │
│      └──────────────────────────────────────────────┘        │
│                  动态讨论直到达成共识                          │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   管理层 (Management Layer)                  │
│                         ┌─────┐                              │
│                         │ PM  │ 拆解任务、分配执行者           │
│                         └─────┘                              │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   执行层 (Execution Layer)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Developer │  │ Designer │  │    QA    │  │ Operator │    │
│  │   代码    │  │   设计   │  │   测试   │  │   部署   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                   并行执行 + 依赖调度                          │
└─────────────────────────────────────────────────────────────┘
```

## 技术亮点

### 1. 动态发言队列
- Agent可根据议题内容动态决定发言顺序
- 非固定轮转，提高讨论效率
- 支持"跳过"信号，无意见Agent自动跳过

### 2. 滑动窗口摘要
- 长讨论自动压缩历史消息
- 保留关键决策点，控制Token消耗
- 支持上下文窗口配置

### 3. 共识检测
- 自动识别讨论是否达成共识
- 关键词匹配 + 结构化输出解析
- 达成共识后自动终止，避免无效轮次

### 4. 三层编排架构
- 决策层：C-Level讨论（战略决策）
- 管理层：PM拆解（任务规划）
- 执行层：专业Agent执行（落地交付）

### 5. 依赖感知调度
- 任务依赖图自动解析
- 无依赖任务并行执行
- 有依赖任务按拓扑序执行

### 6. 双引擎支持
- **DiscussionEngine**：动态讨论，适合开放性议题
- **LangGraph**：状态机流程，适合固定流程场景

## 快速开始

### 安装

```bash
git clone https://github.com/your-username/ai_os.git
cd ai_os
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件：

```env
GLM_API_KEY=your_api_key_here
# 或使用 OpenAI
# OPENAI_API_KEY=your_api_key_here
```

### CLI 模式

```bash
# 动态讨论模式
python run.py "是否应该采用微服务架构？"

# 完整工作流（讨论→拆解→执行）
python run.py "开发一个用户认证系统" --workflow

# 带监控面板
python run.py "议题" --monitor
```

### Web 模式

```bash
python run.py --web
# 访问 http://localhost:8765
```

## 项目结构

```
ai_os/
├── run.py                    # CLI入口
├── requirements.txt
├── src/
│   ├── discussion/
│   │   ├── engine.py         # ★ DiscussionEngine核心
│   │   └── monitor.py        # 实时监控面板
│   ├── execution/
│   │   ├── workflow.py       # ★ WorkflowEngine三层编排
│   │   └── agents.py         # 执行层Agent定义
│   ├── agents/
│   │   ├── ceo.py            # CEO Agent节点
│   │   ├── cfo.py            # CFO Agent节点
│   │   ├── cto.py            # CTO Agent节点
│   │   ├── cmo.py            # CMO Agent节点
│   │   └── cso.py            # CSO Agent节点
│   ├── graph/
│   │   ├── app.py            # LangGraph 5-Agent流程
│   │   ├── four_agent_app.py # LangGraph 4-Agent流程
│   │   └── state.py          # 状态定义
│   ├── config/
│   │   └── settings.py       # 配置管理
│   ├── db/
│   │   └── database.py       # SQLite持久化
│   ├── auth/
│   │   └── auth.py           # 用户认证
│   └── web/
│       └── app.py            # Flask Web界面
└── logs/                     # 讨论日志（自动生成）
```

## 核心类说明

### DiscussionEngine

```python
from discussion.engine import DiscussionEngine, DiscussionConfig

config = DiscussionConfig(
    max_rounds=5,
    context_window=4000,
    skip_signals=["我无异议", "同意以上意见"]
)

engine = DiscussionEngine(config)
result = engine.run("是否应该采用微服务架构？")
```

### WorkflowEngine

```python
from execution.workflow import WorkflowEngine
from execution.agents import TaskScheduler

scheduler = TaskScheduler()
workflow = WorkflowEngine(scheduler)

result = workflow.run(
    topic="开发用户认证系统",
    dry_run=False  # True时只规划不执行
)
```

## Agent角色定义

| 角色 | 职责 | 关注点 |
|------|------|--------|
| CEO | 战略决策 | 整体方向、资源配置 |
| CFO | 财务评估 | ROI、成本效益 |
| CTO | 技术评估 | 可行性、技术风险 |
| CMO | 市场评估 | 用户价值、市场接受度 |
| CSO | 销售评估 | 客户接受度、定价策略 |
| PM | 任务拆解 | 执行计划、依赖管理 |
| Developer | 代码开发 | 功能实现 |
| Designer | 设计输出 | UI/UX设计 |
| QA | 质量保证 | 测试验证 |
| Operator | 运维部署 | 环境配置、上线 |

## 技术栈

- **LLM调用**: httpx (异步HTTP) / LangChain
- **状态管理**: LangGraph (StateGraph)
- **Web框架**: Flask + SQLite
- **认证**: SHA256 + Salt + Session Token
- **监控**: 内嵌HTTP服务器 + 实时JSON状态

## 扩展方式

### 添加新Agent

```python
# src/agents/new_role.py
from utils.hermes_client import call_hermes_agent

def new_role_node(state: AgentState) -> dict:
    response = call_hermes_agent("NEW_ROLE", state["topic"], state["messages"])
    return {
        "messages": [...state["messages"], {"agent": "NEW_ROLE", "content": response}],
        "next_agent": "CEO"
    }
```

### 添加新执行器

```python
# src/execution/agents.py
class NewAgent(BaseAgent):
    name = "new_agent"
    tools = ["custom_tool"]
    
    async def execute(self, task: Task) -> ToolResult:
        # 实现逻辑
        return ToolResult(success=True, output="...")
```

## License

MIT License - 可自由用于商业项目

## Author

AI创世者 - [aicreator.ren](https://aicreator.ren)
