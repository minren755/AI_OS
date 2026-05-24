"""
CEO Agent节点（Hermes Gateway版本）

通过Hermes Gateway API调用，获得完整Agent能力
"""

from src.graph.state import AgentState, Message, MAX_ROUNDS
from src.utils.hermes_client import call_hermes_agent


def ceo_node(state: AgentState) -> dict:
    """
    CEO节点：战略视角讨论
    
    通过Gateway调用，自动获得：
    - CEO角色Memory（战略决策、性格特点）
    - Skills能力
    - Tools工具
    """
    topic = state["topic"]
    messages = state["messages"]
    round_count = state["round_count"]
    
    # 构建讨论上下文
    if round_count == 0:
        # CEO开启讨论
        user_message = f"请从战略角度开启讨论：{topic}"
    else:
        # 继续讨论，传入历史
        history = "\n".join([
            f"[{m['agent']}]: {m['content']}"
            for m in messages[-6:]  # 最近6条
        ])
        user_message = f"""议题：{topic}

讨论记录：
{history}

请CEO从战略角度回应。要求：
1. 如果认同其他Agent的观点，明确说"同意"
2. 如果有分歧，提出具体质疑
3. 给出你的判断：是否推进、需要什么条件
4. 控制在100字以内"""

    # 调用CEO Gateway
    content = call_hermes_agent("CEO", user_message, timeout=60.0)
    
    # 判断是否达成共识
    consensus = _check_consensus(content, messages)
    
    # 决定下一个Agent
    next_agent = "CFO" if not consensus else "END"
    
    # 构建返回的Message
    new_message: Message = {
        "agent": "CEO",
        "content": content,
        "round": round_count + 1,
    }
    
    return {
        "messages": [new_message],
        "round_count": round_count + 1,
        "consensus": consensus,
        "decision": content if consensus else "",
        "next_agent": next_agent,
    }


def _check_consensus(content: str, messages: list) -> bool:
    """
    判断是否达成共识
    
    简单规则：
    - 第1-2轮不可能共识
    - 第3轮后，如果CEO说"同意"且CFO也说"同意"，则共识
    """
    if len(messages) < 4:
        return False
    
    # 检查最近是否有分歧表达
    disagreement_keywords = ["但是", "不过", "质疑", "分歧", "不同意", "风险"]
    if any(kw in content for kw in disagreement_keywords):
        return False
    
    # 检查是否明确同意
    agreement_keywords = ["同意", "认可", "支持", "可以推进", "没问题"]
    if any(kw in content for kw in agreement_keywords):
        return True
    
    return False