"""
AI_OS LangGraph四Agent图（CEO+CFO+CTO+CMO）

完整讨论流程
"""

from langgraph.graph import StateGraph, END

from src.graph.state import AgentState, MAX_ROUNDS
from src.agents import ceo_node, cfo_node, cto_node, cmo_node


def should_continue(state: AgentState) -> str:
    """判断是否继续讨论"""
    if state.get("consensus", False):
        return "end"
    if state.get("round_count", 0) >= MAX_ROUNDS:
        return "end"
    return "continue"


def route_next(state: AgentState) -> str:
    """路由到下一个Agent"""
    next_agent = state.get("next_agent", "CEO")
    if next_agent == "END":
        return END
    return next_agent


def build_four_agent_graph() -> StateGraph:
    """构建四Agent协作图"""
    graph = StateGraph(AgentState)
    
    # 添加四个Agent节点
    graph.add_node("CEO", ceo_node)
    graph.add_node("CFO", cfo_node)
    graph.add_node("CTO", cto_node)
    graph.add_node("CMO", cmo_node)
    
    # 入口：CEO
    graph.set_entry_point("CEO")
    
    # CEO → CFO
    graph.add_edge("CEO", "CFO")
    
    # CFO → CTO
    graph.add_edge("CFO", "CTO")
    
    # CTO → CMO
    graph.add_edge("CTO", "CMO")
    
    # CMO → 条件路由（继续回CEO，或结束）
    graph.add_conditional_edges(
        "CMO",
        should_continue,
        {
            "continue": "CEO",
            "end": END,
        }
    )
    
    return graph


def compile_four_agent_graph():
    """编译四Agent图"""
    graph = build_four_agent_graph()
    return graph.compile()


# 全局实例
four_agent_app = compile_four_agent_graph()
