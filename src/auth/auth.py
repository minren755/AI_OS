"""
AI_OS 用户认证模块
"""
import hashlib
import secrets
from typing import Optional, Dict


def hash_password(password: str) -> str:
    """密码哈希（SHA256 + salt）"""
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hash_value}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, hash_value = password_hash.split('$')
        input_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return input_hash == hash_value
    except:
        return False


# Session管理（简单版，存内存）
# 生产环境应该用Redis
sessions: Dict[str, int] = {}  # session_token -> user_id


def create_session(user_id: int) -> str:
    """创建session token"""
    token = secrets.token_urlsafe(32)
    sessions[token] = user_id
    return token


def get_user_from_session(token: str) -> Optional[int]:
    """从session获取user_id"""
    return sessions.get(token)


def delete_session(token: str):
    """删除session（登出）"""
    sessions.pop(token, None)


if __name__ == "__main__":
    # 测试密码哈希
    pwd = "test123"
    hashed = hash_password(pwd)
    print(f"Hashed: {hashed}")
    print(f"Verify correct: {verify_password(pwd, hashed)}")
    print(f"Verify wrong: {verify_password('wrong', hashed)}")