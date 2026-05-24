"""
CTO Agent节点（Hermes Gateway版本）

通过Hermes Gateway API调用，获得完整Agent能力
"""

from src.graph.state import AgentState, Message
from src.utils.hermes_client import call_hermes_agent


def cto_node(state: AgentState) -> dict:
    """
    CTO节点：技术视角讨论
    
    通过Gateway调用，自动获得：
    - CTO角色Memory（技术背景、性格特点）
    - Skills能力
    - Tools工具
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

请CTO从技术角度回应。要求：
1. 评估技术可行性（能做/难做/做不了）
2. 给出工期估算（人天）
3. 指出技术风险点
4. 控制在100字以内"""

    # 调用CTO Gateway
    content = call_hermes_agent("CTO", user_message, timeout=60.0)
    
    # 构建返回的Message
    new_message: Message = {
        "agent": "CTO",
        "content": content,
        "round": round_count + 1,
    }
    
    # 下一个Agent
    next_agent = "CMO"
    
    return {
        "messages": [new_message],
        "next_agent": next_agent,
    }
