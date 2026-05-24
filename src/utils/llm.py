"""
LLM调用工具

封装langchain ChatOpenAI，提供统一的LLM调用接口
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.config.settings import get_llm_config


def create_llm() -> ChatOpenAI:
    """创建LLM实例"""
    config = get_llm_config()
    
    llm = ChatOpenAI(
        model=config["model"],
        base_url=config["base_url"],
        api_key=config["api_key"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )
    return llm


def call_llm(system_prompt: str, user_message: str) -> str:
    """
    调用LLM获取回复
    
    Args:
        system_prompt: 系统提示词（角色设定）
        user_message: 用户消息
        
    Returns:
        LLM回复文本
    """
    llm = create_llm()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    
    response = llm.invoke(messages)
    return response.content
