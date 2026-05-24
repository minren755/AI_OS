"""
CFO Agent节点（Hermes Gateway版本）

通过Hermes Gateway API调用，获得完整Agent能力
"""

from src.graph.state import AgentState, Message
from src.utils.hermes_client import call_hermes_agent


def cfo_node(state: AgentState) -> dict:
    """
    CFO节点：财务视角讨论
    
    通过Gateway调用，自动获得：
    - CFO角色Memory（财务数据、性格特点）
    - Skills能力
    - Tools工具（可查数据库、算ROI）
    """
    topic = state["topic"]
    messages = state["messages"]
    round_count = state["round_count"]
    
    # 构建讨论上下文
    history = "\n".join([
        f"[{m['agent']}]: {m['content']}"
        for m in messages[-6:]  # 最近6条
    ])
    
    user_message = f"""议题：{topic}

讨论记录：
{history}

请CFO从财务角度回应。要求：
1. 先看ROI和回款周期
2. 指出财务风险点
3. 明确说"同意"或"质疑"
4. 控制在100字以内"""

    # 调用CFO Gateway
    content = call_hermes_agent("CFO", user_message, timeout=60.0)
    
    # 决定下一个Agent
    next_agent = "CEO"  # 返回CEO继续讨论
    
    # 构建返回的Message
    new_message: Message = {
        "agent": "CFO",
        "content": content,
        "round": round_count + 1,
    }
    
    return {
        "messages": [new_message],
        "round_count": round_count,
        "consensus": False,
        "decision": "",
        "next_agent": next_agent,
    }