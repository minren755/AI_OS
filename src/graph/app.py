"""
AI_OS LangGraph图定义

构建多Agent讨论流程：
CEO → CFO → CTO → CMO → CSO → (循环) → END
"""

from langgraph.graph import StateGraph, END

from src.graph.state import AgentState, MAX_ROUNDS
from src.agents import ceo_node, cfo_node, cto_node, cmo_node, cso_node


def should_continue(state: AgentState) -> str:
    """
    条件边：判断是否继续讨论
    
    返回：
    - "continue": 继续下一个Agent
    - "end": 结束讨论
    """
    # 达成共识则结束
    if state.get("consensus", False):
        return "end"
    
    # 超过最大轮次则结束
    if state.get("round_count", 0) >= MAX_ROUNDS:
        return "end"
    
    # 否则继续
    return "continue"


def route_next_agent(state: AgentState) -> str:
    """
    路由到下一个Agent节点
    """
    next_agent = state.get("next_agent", "CEO")
    
    if next_agent == "END":
        return END
    
    return next_agent


def build_graph() -> StateGraph:
    """
    构建AI_OS讨论图
    """
    graph = StateGraph(AgentState)
    
    # 添加所有战略层Agent节点
    graph.add_node("CEO", ceo_node)
    graph.add_node("CFO", cfo_node)
    graph.add_node("CTO", cto_node)
    graph.add_node("CMO", cmo_node)
    graph.add_node("CSO", cso_node)
    
    # 设置入口：从CEO开始
    graph.set_entry_point("CEO")
    
    # 添加边：CEO → CFO
    graph.add_edge("CEO", "CFO")
    
    # 添加边：CFO → CTO
    graph.add_edge("CFO", "CTO")
    
    # 添加边：CTO → CMO
    graph.add_edge("CTO", "CMO")
    
    # 添加边：CMO → CSO
    graph.add_edge("CMO", "CSO")
    
    # CSO → 条件路由（继续循环或结束）
    graph.add_conditional_edges(
        "CSO",
        should_continue,
        {
            "continue": "CEO",  # 循环回CEO
            "end": END,
        }
    )
    
    return graph


def compile_graph():
    """
    编译图，返回可执行的Runnable
    """
    graph = build_graph()
    return graph.compile()


# 创建全局实例
app = compile_graph()
