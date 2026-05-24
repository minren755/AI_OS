"""
Hermes Gateway API客户端

用于调用独立Gateway实例（CEO/CFO/CTO等）
"""

import httpx
from typing import Optional


# Gateway端口配置
GATEWAY_PORTS = {
    "CEO": 8643,
    "CFO": 8644,
    "CTO": 8645,  # 待创建
    "CMO": 8646,  # 待创建
    "CSO": 8647,  # 待创建
}


def call_hermes_agent(
    agent_role: str,
    user_message: str,
    system_prompt: Optional[str] = None,
    timeout: float = 60.0,
) -> str:
    """
    调用指定角色的Hermes Gateway实例
    
    Args:
        agent_role: Agent角色（CEO/CFO/CTO/CMO/CSO）
        user_message: 用户消息
        system_prompt: 可选的system prompt（Gateway已有角色设定）
        timeout: 请求超时时间
    
    Returns:
        Agent的回复内容
    """
    port = GATEWAY_PORTS.get(agent_role)
    if not port:
        raise ValueError(f"未知的Agent角色: {agent_role}")
    
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = httpx.post(
            url,
            json={
                "model": "hermes-agent",
                "messages": messages,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        return f"[{agent_role}响应超时]"
    except httpx.HTTPStatusError as e:
        return f"[{agent_role}HTTP错误: {e.response.status_code}]"
    except Exception as e:
        return f"[{agent_role}调用失败: {str(e)}]"


def check_gateway_health(agent_role: str) -> bool:
    """检查指定Gateway实例是否健康"""
    port = GATEWAY_PORTS.get(agent_role)
    if not port:
        return False
    
    try:
        response = httpx.get(
            f"http://127.0.0.1:{port}/health",
            timeout=5.0,
        )
        return response.status_code == 200
    except:
        return False