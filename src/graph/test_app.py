"""
AI_OS LangGraph简化图（仅CEO+CFO测试）

用于验证Hermes Gateway集成
"""

from langgraph.graph import StateGraph, END

from src.graph.state import AgentState, MAX_ROUNDS
from src.agents import ceo_node, cfo_node


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


def build_test_graph() -> StateGraph:
    """构建CEO+CFO测试图"""
    graph = StateGraph(AgentState)
    
    # 只添加CEO和CFO节点
    graph.add_node("CEO", ceo_node)
    graph.add_node("CFO", cfo_node)
    
    # 入口：CEO
    graph.set_entry_point("CEO")
    
    # CEO → CFO
    graph.add_edge("CEO", "CFO")
    
    # CFO → 条件路由
    graph.add_conditional_edges(
        "CFO",
        should_continue,
        {
            "continue": "CEO",
            "end": END,
        }
    )
    
    return graph


def compile_test_graph():
    """编译测试图"""
    graph = build_test_graph()
    return graph.compile()


# 全局实例
test_app = compile_test_graph()