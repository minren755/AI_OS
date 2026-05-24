"""
CSO Agent节点（Hermes Gateway版本）

通过Hermes Gateway API调用，获得完整Agent能力
"""

from src.graph.state import AgentState, Message
from src.utils.hermes_client import call_hermes_agent


def cso_node(state: AgentState) -> dict:
    """
    CSO节点：销售视角讨论
    
    通过Gateway调用，自动获得：
    - CSO角色Memory（销售背景、性格特点）
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

请CSO从销售角度回应。要求：
1. 评估客户接受度和签约可能性
2. 分析定价和商务条件
3. 给出销售建议
4. 控制在100字以内"""

    # 调用CSO Gateway
    content = call_hermes_agent("CSO", user_message, timeout=60.0)
    
    # 构建返回的Message
    new_message: Message = {
        "agent": "CSO",
        "content": content,
        "round": round_count + 1,
    }
    
    # CSO是最后一环，下一个回到CEO
    next_agent = "CEO"
    
    return {
        "messages": [new_message],
        "next_agent": next_agent,
    }
