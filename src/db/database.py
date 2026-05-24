"""
AI_OS 数据库模块 - SQLite
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json

# 动态获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "aios.db"


def init_db():
    """初始化数据库"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT,
        company TEXT,
        title TEXT,
        credits INTEGER DEFAULT 5,
        created_at TEXT NOT NULL,
        last_login TEXT
    )
    """)
    
    # 讨论记录表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discussions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic TEXT NOT NULL,
        rounds INTEGER,
        consensus BOOLEAN,
        tokens_used INTEGER,
        result TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    # 讨论消息表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discussion_id INTEGER NOT NULL,
        round INTEGER NOT NULL,
        agent TEXT NOT NULL,
        content TEXT,
        satisfied BOOLEAN,
        skipped BOOLEAN,
        created_at TEXT NOT NULL,
        FOREIGN KEY (discussion_id) REFERENCES discussions(id)
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")


def get_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)


# ============================================
# 用户操作
# ============================================

def create_user(email: str, password_hash: str, name: str = None, 
                company: str = None, title: str = None) -> int:
    """创建用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO users (email, password_hash, name, company, title, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (email, password_hash, name, company, title, datetime.now().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        # 邮箱已存在
        return -1
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    """通过邮箱获取用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, email, password_hash, name, company, title, credits, created_at, last_login
    FROM users WHERE email = ?
    """, (email,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "name": row[3],
            "company": row[4],
            "title": row[5],
            "credits": row[6],
            "created_at": row[7],
            "last_login": row[8]
        }
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """通过ID获取用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, email, password_hash, name, company, title, credits, created_at, last_login
    FROM users WHERE id = ?
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "name": row[3],
            "company": row[4],
            "title": row[5],
            "credits": row[6],
            "created_at": row[7],
            "last_login": row[8]
        }
    return None


def update_last_login(user_id: int):
    """更新最后登录时间"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE users SET last_login = ? WHERE id = ?
    """, (datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()


# ============================================
# 额度操作
# ============================================

def get_credits(user_id: int) -> int:
    """获取用户剩余额度"""
    user = get_user_by_id(user_id)
    return user["credits"] if user else 0


def use_credit(user_id: int, amount: int = 1) -> bool:
    """扣减额度"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 先检查额度
    cursor.execute("SELECT credits FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or row[0] < amount:
        conn.close()
        return False
    
    # 扣减
    cursor.execute("""
    UPDATE users SET credits = credits - ? WHERE id = ?
    """, (amount, user_id))
    
    conn.commit()
    conn.close()
    return True


def add_credits(user_id: int, amount: int):
    """增加额度（付费后调用）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE users SET credits = credits + ? WHERE id = ?
    """, (amount, user_id))
    
    conn.commit()
    conn.close()


# ============================================
# 讨论记录操作
# ============================================

def save_discussion(user_id: int, topic: str, result: Dict, 
                    rounds: int, consensus: bool, tokens_used: int = 0) -> int:
    """保存讨论记录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO discussions (user_id, topic, rounds, consensus, tokens_used, result, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, topic, rounds, consensus, tokens_used, 
          json.dumps(result, ensure_ascii=False), datetime.now().isoformat()))
    
    discussion_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return discussion_id


def save_message(discussion_id: int, round: int, agent: str, 
                 content: str, satisfied: bool = False, skipped: bool = False):
    """保存单条消息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO messages (discussion_id, round, agent, content, satisfied, skipped, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (discussion_id, round, agent, content, satisfied, skipped, 
          datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_user_discussions(user_id: int, limit: int = 20) -> List[Dict]:
    """获取用户的讨论历史"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, topic, rounds, consensus, created_at
    FROM discussions 
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    """, (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "topic": row[1],
            "rounds": row[2],
            "consensus": row[3],
            "created_at": row[4]
        }
        for row in rows
    ]


def get_discussion_detail(discussion_id: int) -> Optional[Dict]:
    """获取讨论详情"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, user_id, topic, rounds, consensus, result, created_at
    FROM discussions WHERE id = ?
    """, (discussion_id,))
    
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    # 获取消息
    cursor.execute("""
    SELECT round, agent, content, satisfied, skipped
    FROM messages WHERE discussion_id = ?
    ORDER BY round, id
    """, (discussion_id,))
    
    messages = cursor.fetchall()
    conn.close()
    
    return {
        "id": row[0],
        "user_id": row[1],
        "topic": row[2],
        "rounds": row[3],
        "consensus": row[4],
        "result": json.loads(row[5]) if row[5] else None,
        "created_at": row[6],
        "messages": [
            {
                "round": m[0],
                "agent": m[1],
                "content": m[2],
                "satisfied": m[3],
                "skipped": m[4]
            }
            for m in messages
        ]
    }


if __name__ == "__main__":
    init_db()