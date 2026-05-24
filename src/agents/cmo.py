"""
CMO Agent节点（Hermes Gateway版本）

通过Hermes Gateway API调用，获得完整Agent能力
"""

from src.graph.state import AgentState, Message
from src.utils.hermes_client import call_hermes_agent


def cmo_node(state: AgentState) -> dict:
    """
    CMO节点：营销视角讨论
    
    通过Gateway调用，自动获得：
    - CMO角色Memory（营销背景、性格特点）
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

请CMO从营销角度回应。要求：
1. 评估市场价值和传播效果
2. 分析客户接受度和标杆潜力
3. 给出营销建议
4. 控制在100字以内"""

    # 调用CMO Gateway
    content = call_hermes_agent("CMO", user_message, timeout=60.0)
    
    # 构建返回的Message
    new_message: Message = {
        "agent": "CMO",
        "content": content,
        "round": round_count + 1,
    }
    
    # 下一个Agent
    next_agent = "CSO"
    
    return {
        "messages": [new_message],
        "next_agent": next_agent,
    }
