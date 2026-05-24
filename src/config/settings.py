"""
AI_OS 配置模块

从环境变量或Hermes配置加载LLM API配置
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# .env文件路径
ENV_FILE = PROJECT_ROOT / ".env"


# LLM配置（使用腾讯混元glm-5）
LLM_CONFIG = {
    "model": "glm-5",
    "base_url": "https://api.lkeap.cloud.tencent.com/coding/v3",
    "api_key": "",  # 从环境变量加载
    "temperature": 0.7,
    "max_tokens": 1000,
}


def load_api_key():
    """加载API key"""
    # 优先从环境变量
    api_key = os.getenv("GLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if api_key:
        return api_key
    
    # 尝试从.env文件加载
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GLM_API_KEY="):
                    return line.split("=", 1)[1].strip('"\'')
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip('"\'')
    
    return None


def get_llm_config():
    """获取LLM配置"""
    config = LLM_CONFIG.copy()
    api_key = load_api_key()
    
    if api_key:
        config["api_key"] = api_key
    
    return config


# Redis配置
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
}
