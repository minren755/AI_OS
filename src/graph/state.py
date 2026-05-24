"""
AI_OS AgentState定义
所有Agent节点共享的状态结构
"""

from typing import TypedDict, Annotated
from operator import add


class Message(TypedDict):
    """单条讨论消息"""
    agent: str       # 发言Agent角色（CEO/CFO/CTO/CMO/CSO）
    content: str     # 发言内容


class AgentState(TypedDict):
    """
    AI_OS全局状态
    
    所有Agent通过此State通信，LangGraph负责状态流转。
    """
    # 讨论相关
    topic: str                                    # 当前讨论议题
    messages: Annotated[list[Message], add]       # 讨论历史（累积追加）
    round_count: int                              # 当前讨论轮次
    
    # 决策相关
    consensus: bool                               # 是否达成共识
    decision: str                                 # 最终决策结论
    dissent: str                                  # 分歧点（未达共识时记录）
    
    # 路由相关
    next_agent: str                               # 下一个发言的Agent
    
    # 执行相关（后续阶段使用）
    tasks: list[dict]                             # 需要Hermes执行的任务
    results: list[dict]                           # Hermes执行结果


# 讨论轮次上限（防止无限循环）
MAX_ROUNDS = 5

# Agent角色列表
AGENT_ROLES = ["CEO", "CFO", "CTO", "CMO", "CSO"]
