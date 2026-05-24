"""
AI_OS 验证码发送模块
使用新浪邮箱SMTP发送验证码（个人品牌邮箱）
"""
import os
import smtplib
from email.mime.text import MIMEText
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional

# 验证码临时存储（生产环境应该用Redis）
verify_codes: Dict[str, Dict] = {}

# 新浪邮箱配置（个人品牌邮箱 aicreator@sina.com）
SMTP_SERVER = 'smtp.sina.com'
SMTP_PORT = 465
SMTP_USER = 'aicreator@sina.com'
# 授权码从环境变量读取
SMTP_PASSWORD = os.environ.get('AIOS_SMTP_PASSWORD', 'ab606fe4c810d523')


def generate_code(length: int = 6) -> str:
    """生成随机验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_verify_code(email: str) -> tuple[bool, str]:
    """发送验证码到邮箱"""
    # 生成验证码
    code = generate_code()
    
    # 存储验证码（有效期5分钟）
    verify_codes[email] = {
        "code": code,
        "expires": datetime.now() + timedelta(minutes=5),
        "created": datetime.now()
    }
    
    # 构建邮件
    subject = "AI_OS 注册验证码"
    body = f"""
您的AI_OS注册验证码是：{code}

验证码5分钟内有效，请尽快完成注册。

如果这不是您的操作，请忽略此邮件。

AI_OS - 多Agent协作系统
"""
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = email
    
    # 发送
    try:
        smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_USER, [email], msg.as_string())
        smtp.quit()
        
        print(f"验证码已发送到 {email}: {code}")
        return True, code
    except Exception as e:
        print(f"发送失败: {e}")
        return False, str(e)


def verify_code(email: str, code: str) -> bool:
    """验证验证码"""
    if email not in verify_codes:
        return False
    
    stored = verify_codes[email]
    
    # 检查是否过期
    if datetime.now() > stored["expires"]:
        del verify_codes[email]
        return False
    
    # 检查是否匹配
    if stored["code"] != code:
        return False
    
    # 验证成功，删除验证码
    del verify_codes[email]
    return True


def get_code_for_test(email: str) -> Optional[str]:
    """获取验证码（仅用于测试）"""
    if email in verify_codes:
        return verify_codes[email]["code"]
    return None


if __name__ == "__main__":
    # 测试
    email = "test@example.com"
    success, result = send_verify_code(email)
    if success:
        print(f"发送成功，验证码: {result}")
        # 验证
        print(f"验证正确: {verify_code(email, result)}")
        print(f"验证错误: {verify_code(email, '000000')}")
    else:
        print(f"发送失败: {result}")