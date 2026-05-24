"""
AI_OS Web界面 - 带用户系统
Flask + SQLite + 用户认证
"""
import os
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, Response, render_template_string

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    get_credits, use_credit, save_discussion, save_message,
    get_user_discussions, get_discussion_detail, update_last_login
)
from auth.auth import (
    hash_password, verify_password, create_session, 
    get_user_from_session, delete_session
)
from discussion.engine import DiscussionEngine, DiscussionConfig


app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('AIOS_SECRET_KEY', 'dev-only-fallback-key')

# 当前进行中的讨论（内存中，按session隔离）
current_discussions = {}


# ============================================
# 认证装饰器
# ============================================

def require_auth(f):
    """需要登录才能访问"""
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_from_session(token)
        if not user_id:
            return jsonify({"error": "请先登录"}), 401
        request.user_id = user_id
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# ============================================
# 页面路由
# ============================================

@app.route('/')
def index():
    """公开首页"""
    from flask import render_template
    return render_template('landing.html')


@app.route('/app')
def main_app():
    """主应用页面（登录/讨论）"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/test')
def test_page():
    """交互测试页面"""
    from flask import render_template
    return render_template('test_interactive.html')


@app.route('/api/test/check', methods=['POST'])
def test_check():
    """测试专用API（无需登录）"""
    data = request.json
    topic = data.get('topic', '').strip()
    
    if not topic:
        return jsonify({"error": "请输入主题"}), 400
    
    # ===== 方案B：信息完整性检查 =====
    from execution.info_checker import check_and_ask
    info_check = check_and_ask(topic)
    
    if info_check["need_input"]:
        return jsonify({
            "status": "need_input",
            "questions": info_check["questions"],
            "prompt": info_check["prompt"],
            "missing": info_check["missing"]
        })
    else:
        return jsonify({
            "status": "ok",
            "message": "信息完整，可以直接讨论"
        })


@app.route('/api/test/continue', methods=['POST'])
def test_continue():
    """测试继续API（无需登录）"""
    data = request.json
    topic = data.get('topic', '').strip()
    user_input = data.get('user_input', '').strip()
    
    # 合并主题和用户补充
    if user_input and user_input != "继续":
        enhanced_topic = topic + "\n\n用户补充信息：" + user_input
    else:
        enhanced_topic = topic
    
    # 再次检查信息完整性
    from execution.info_checker import check_and_ask
    info_check = check_and_ask(enhanced_topic)
    
    return jsonify({
        "status": "ready",
        "enhanced_topic": enhanced_topic,
        "info_complete": not info_check["need_input"],
        "message": "信息已补充，可以开始讨论（需登录后调用/api/start）"
    })


# ============================================
# 认证API
# ============================================

@app.route('/api/send-code', methods=['POST'])
def send_code():
    """发送验证码"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({"error": "请输入邮箱"}), 400
    
    # 检查邮箱格式
    if '@' not in email or '.' not in email:
        return jsonify({"error": "邮箱格式不正确"}), 400
    
    # 发送验证码
    from src.auth.email_verify import send_verify_code
    success, result = send_verify_code(email)
    
    if success:
        return jsonify({"message": "验证码已发送"})
    else:
        return jsonify({"error": f"发送失败: {result}"}), 500


@app.route('/api/register', methods=['POST'])
def register():
    """注册"""
    data = request.json
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()
    company = data.get('company', '').strip()
    title = data.get('title', '').strip()
    
    # 校验
    if not email or not password:
        return jsonify({"error": "邮箱和密码不能为空"}), 400
    if not code:
        return jsonify({"error": "请输入验证码"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少6位"}), 400
    
    # 验证验证码
    from src.auth.email_verify import verify_code
    if not verify_code(email, code):
        return jsonify({"error": "验证码错误或已过期"}), 400
    
    # 检查邮箱是否已注册
    if get_user_by_email(email):
        return jsonify({"error": "邮箱已注册"}), 400
    
    # 创建用户
    password_hash = hash_password(password)
    user_id = create_user(email, password_hash, name, company, title)
    
    if user_id < 0:
        return jsonify({"error": "注册失败"}), 500
    
    # 自动登录
    token = create_session(user_id)
    user = get_user_by_id(user_id)
    
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "credits": user["credits"]
        }
    })


@app.route('/api/login', methods=['POST'])
def login():
    """登录"""
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return jsonify({"error": "邮箱和密码不能为空"}), 400
    
    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "邮箱未注册"}), 404
    
    if not verify_password(password, user["password_hash"]):
        return jsonify({"error": "密码错误"}), 401
    
    # 更新登录时间
    update_last_login(user["id"])
    
    # 创建session
    token = create_session(user["id"])
    
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "credits": user["credits"]
        }
    })


@app.route('/api/logout', methods=['POST'])
@require_auth
def logout():
    """登出"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    delete_session(token)
    return jsonify({"message": "已登出"})


@app.route('/api/user/info', methods=['GET'])
@require_auth
def user_info():
    """获取用户信息"""
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    
    return jsonify({
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "company": user["company"],
        "title": user["title"],
        "credits": user["credits"],
        "created_at": user["created_at"]
    })


# ============================================
# 讨论API
# ============================================

@app.route('/api/start', methods=['POST'])
@require_auth
def start_discussion():
    """开始讨论"""
    # 检查额度
    credits = get_credits(request.user_id)
    if credits <= 0:
        return jsonify({"error": "额度不足，请联系管理员"}), 403
    
    data = request.json
    topic = data.get('topic', '').strip()
    max_rounds = data.get('max_rounds', 3)
    
    if not topic:
        return jsonify({"error": "请输入议题"}), 400
    
    # ===== 方案B：信息完整性检查 =====
    from execution.info_checker import check_and_ask
    info_check = check_and_ask(topic)
    
    if info_check["need_input"]:
        # 返回需要补充的问题，不扣额度
        return jsonify({
            "status": "need_input",
            "questions": info_check["questions"],
            "prompt": info_check["prompt"],
            "missing": info_check["missing"]
        })
    
    # 扣减额度
    if not use_credit(request.user_id):
        return jsonify({"error": "额度不足"}), 403
    
    # 生成session key
    session_key = f"{request.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 初始化讨论状态
    current_discussions[session_key] = {
        "running": True,
        "topic": topic,
        "user_id": request.user_id,
        "events": [],
        "round": 0,
        "agents": {
            "CEO": {"status": "等待中", "content": "", "satisfied": False},
            "CFO": {"status": "等待中", "content": "", "satisfied": False},
            "CTO": {"status": "等待中", "content": "", "satisfied": False},
            "CMO": {"status": "等待中", "content": "", "satisfied": False}
        },
        "history": [],
        "consensus": False
    }
    
    # 异步执行讨论
    def emit_event(event_dict):
        event_dict["time"] = datetime.now().strftime("%H:%M:%S")
        current_discussions[session_key]["events"].append(event_dict)
        
        # 更新agent状态
        event_type = event_dict.get("type", "")
        data = event_dict
        
        if event_type == "agent_start":
            agent = data.get("agent", "")
            if agent in current_discussions[session_key]["agents"]:
                current_discussions[session_key]["agents"][agent]["status"] = "发言中..."
        
        elif event_type == "agent_done":
            agent = data.get("agent", "")
            content = data.get("content", "")
            satisfied = data.get("satisfied", False)
            skipped = data.get("skipped", False)
            
            if agent in current_discussions[session_key]["agents"]:
                current_discussions[session_key]["agents"][agent]["status"] = "完成"
                current_discussions[session_key]["agents"][agent]["content"] = content
                current_discussions[session_key]["agents"][agent]["satisfied"] = satisfied
            
            current_discussions[session_key]["history"].append({
                "round": current_discussions[session_key]["round"],
                "agent": agent,
                "content": content,
                "satisfied": satisfied,
                "skipped": skipped,
                "time": datetime.now().strftime("%H:%M:%S")
            })
        
        elif event_type == "ceo_summary":
            current_discussions[session_key]["history"].append({
                "round": "总结",
                "agent": "CEO",
                "content": data.get("content", ""),
                "time": datetime.now().strftime("%H:%M:%S")
            })
        
        elif event_type == "round_start":
            current_discussions[session_key]["round"] = data.get("round", 0)
        
        elif event_type == "consensus":
            current_discussions[session_key]["consensus"] = True
    
    # 后台执行讨论
    async def run_discussion_async():
        config = DiscussionConfig(max_rounds=max_rounds)
        engine = DiscussionEngine(config)
        engine.on_event = emit_event
        
        try:
            result = await engine.run(topic)
            
            # 保存到数据库
            discussion_id = save_discussion(
                user_id=request.user_id,
                topic=topic,
                result=result,
                rounds=result.get("总轮数", 0),
                consensus=result.get("共识达成", False)
            )
            
            # 保存每条消息
            for h in current_discussions[session_key]["history"]:
                save_message(
                    discussion_id=discussion_id,
                    round=h.get("round", 0) if isinstance(h.get("round"), int) else 0,
                    agent=h.get("agent", ""),
                    content=h.get("content", ""),
                    satisfied=h.get("satisfied", False),
                    skipped=h.get("skipped", False)
                )
            
            emit_event({"type": "end", "result": result})
            
        except Exception as e:
            emit_event({"type": "error", "message": str(e)})
        finally:
            current_discussions[session_key]["running"] = False
    
    # 在事件循环中运行
    loop = asyncio.new_event_loop()
    import threading
    def run_in_thread():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_discussion_async())
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    return jsonify({
        "status": "started",
        "session_key": session_key,
        "credits_remaining": get_credits(request.user_id)
    })


@app.route('/api/continue', methods=['POST'])
@require_auth
def continue_discussion():
    """用户回答后继续讨论（方案B）"""
    data = request.json
    topic = data.get('topic', '').strip()
    user_input = data.get('user_input', '').strip()
    max_rounds = data.get('max_rounds', 3)
    
    if not topic:
        return jsonify({"error": "请输入议题"}), 400
    
    # 合并主题和用户补充
    if user_input and user_input != "继续":
        enhanced_topic = topic + "\n\n用户补充信息：" + user_input
    else:
        enhanced_topic = topic
    
    # 扣减额度
    if not use_credit(request.user_id):
        return jsonify({"error": "额度不足"}), 403
    
    # 生成session key
    session_key = f"{request.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 初始化讨论状态
    current_discussions[session_key] = {
        "running": True,
        "topic": enhanced_topic,
        "user_id": request.user_id,
        "events": [{"type": "input_received", "input": user_input, "time": datetime.now().strftime("%H:%M:%S")}],
        "round": 0,
        "agents": {
            "CEO": {"status": "等待中", "content": "", "satisfied": False},
            "CFO": {"status": "等待中", "content": "", "satisfied": False},
            "CTO": {"status": "等待中", "content": "", "satisfied": False},
            "CMO": {"status": "等待中", "content": "", "satisfied": False}
        },
        "history": [],
        "consensus": False
    }
    
    # 后台执行讨论（同start_discussion逻辑）
    def emit_event(event_dict):
        event_dict["time"] = datetime.now().strftime("%H:%M:%S")
        current_discussions[session_key]["events"].append(event_dict)
        
        event_type = event_dict.get("type", "")
        if event_type == "agent_start":
            agent = event_dict.get("agent", "")
            if agent in current_discussions[session_key]["agents"]:
                current_discussions[session_key]["agents"][agent]["status"] = "发言中..."
        elif event_type == "agent_done":
            agent = event_dict.get("agent", "")
            content = event_dict.get("content", "")
            satisfied = event_dict.get("satisfied", False)
            skipped = event_dict.get("skipped", False)
            if agent in current_discussions[session_key]["agents"]:
                current_discussions[session_key]["agents"][agent]["status"] = "完成"
                current_discussions[session_key]["agents"][agent]["content"] = content
                current_discussions[session_key]["agents"][agent]["satisfied"] = satisfied
            current_discussions[session_key]["history"].append({
                "round": current_discussions[session_key]["round"],
                "agent": agent, "content": content,
                "satisfied": satisfied, "skipped": skipped,
                "time": datetime.now().strftime("%H:%M:%S")
            })
        elif event_type == "ceo_summary":
            current_discussions[session_key]["history"].append({
                "round": "总结", "agent": "CEO",
                "content": event_dict.get("content", ""),
                "time": datetime.now().strftime("%H:%M:%S")
            })
        elif event_type == "round_start":
            current_discussions[session_key]["round"] = event_dict.get("round", 0)
        elif event_type == "consensus":
            current_discussions[session_key]["consensus"] = True
    
    async def run_discussion_async():
        config = DiscussionConfig(max_rounds=max_rounds)
        engine = DiscussionEngine(config)
        engine.on_event = emit_event
        try:
            result = await engine.run(enhanced_topic)
            discussion_id = save_discussion(
                user_id=request.user_id, topic=enhanced_topic,
                result=result, rounds=result.get("总轮数", 0),
                consensus=result.get("共识达成", False)
            )
            for h in current_discussions[session_key]["history"]:
                save_message(
                    discussion_id=discussion_id,
                    round=h.get("round", 0) if isinstance(h.get("round"), int) else 0,
                    agent=h.get("agent", ""), content=h.get("content", ""),
                    satisfied=h.get("satisfied", False), skipped=h.get("skipped", False)
                )
            emit_event({"type": "end", "result": result})
        except Exception as e:
            emit_event({"type": "error", "message": str(e)})
        finally:
            current_discussions[session_key]["running"] = False
    
    loop = asyncio.new_event_loop()
    import threading
    def run_in_thread():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_discussion_async())
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    return jsonify({
        "status": "started",
        "session_key": session_key,
        "credits_remaining": get_credits(request.user_id)
    })


@app.route('/api/events')
@require_auth
def get_events():
    """获取讨论事件"""
    session_key = request.args.get('session_key', '')
    last_index = int(request.args.get('last', 0))
    
    if session_key not in current_discussions:
        return jsonify({"events": [], "running": False})
    
    disc = current_discussions[session_key]
    
    # 验证用户权限
    if disc["user_id"] != request.user_id:
        return jsonify({"error": "无权访问"}), 403
    
    events = disc["events"][last_index:]
    
    return jsonify({
        "events": events,
        "running": disc["running"],
        "agents": disc["agents"],
        "round": disc["round"],
        "consensus": disc["consensus"],
        "credits": get_credits(request.user_id)
    })


# ============================================
# 历史API
# ============================================

@app.route('/api/history', methods=['GET'])
@require_auth
def get_history():
    """获取讨论历史"""
    discussions = get_user_discussions(request.user_id)
    return jsonify({"discussions": discussions})


@app.route('/api/history/<int:discussion_id>', methods=['GET'])
@require_auth
def get_history_detail(discussion_id):
    """获取讨论详情"""
    detail = get_discussion_detail(discussion_id)
    
    if not detail:
        return jsonify({"error": "讨论不存在"}), 404
    
    # 验证权限
    if detail["user_id"] != request.user_id:
        return jsonify({"error": "无权访问"}), 403
    
    return jsonify(detail)


# ============================================
# 前端HTML
# ============================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI_OS - 多Agent协作系统</title>
    <style>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI_OS - 多Agent协作系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #0a0a1a; color: #fff; font-family: -apple-system, sans-serif;
            min-height: 100vh;
        }
        
        /* 顶部导航 */
        .navbar {
            background: #1a1a2e; padding: 12px 24px;
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid #2a2a4a;
        }
        .navbar .brand { font-size: 20px; font-weight: bold; color: #4cc9f0; }
        .navbar .user-info { font-size: 14px; color: #aaa; display: flex; align-items: center; gap: 12px; }
        .navbar .credits { 
            background: #7209b7; padding: 4px 10px; border-radius: 12px; font-size: 12px;
        }
        .navbar .logout-btn {
            background: none; border: 1px solid #666; color: #aaa; padding: 4px 12px;
            border-radius: 6px; cursor: pointer; font-size: 12px;
        }
        .navbar .logout-btn:hover { border-color: #f72585; color: #f72585; }
        
        /* 认证页面 */
        .auth-page {
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 20px;
        }
        .auth-card {
            background: #1a1a2e; border-radius: 16px; padding: 40px;
            width: 100%; max-width: 420px; border: 1px solid #2a2a4a;
        }
        .auth-card h2 { text-align: center; margin-bottom: 24px; color: #4cc9f0; }
        .auth-card .subtitle { text-align: center; color: #888; margin-bottom: 20px; font-size: 13px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: #aaa; font-size: 13px; }
        .form-group input {
            width: 100%; padding: 10px 14px; background: #0a0a1a; border: 1px solid #2a2a4a;
            border-radius: 8px; color: #fff; font-size: 14px;
        }
        .form-group input:focus { outline: none; border-color: #4cc9f0; }
        .form-row { display: flex; gap: 12px; }
        .form-row .form-group { flex: 1; }
        .auth-btn {
            width: 100%; padding: 12px; background: #4cc9f0; color: #000;
            border: none; border-radius: 8px; font-size: 15px; font-weight: bold;
            cursor: pointer; margin-top: 8px;
        }
        .auth-btn:hover { background: #3aa8d8; }
        .auth-btn:disabled { background: #555; cursor: not-allowed; }
        .auth-switch { text-align: center; margin-top: 16px; color: #888; font-size: 13px; }
        .auth-switch a { color: #4cc9f0; cursor: pointer; }
        .auth-error { color: #f72585; font-size: 13px; margin-top: 8px; text-align: center; }
        
        /* 主页面 */
        .main-page { display: none; }
        .main-page.active { display: block; }
        
        /* 讨论区 */
        .discussion-area {
            max-width: 900px; margin: 20px auto; padding: 0 20px;
        }
        .topic-input {
            display: flex; gap: 12px; margin-bottom: 20px;
        }
        .topic-input input {
            flex: 1; padding: 12px 16px; background: #1a1a2e; border: 1px solid #2a2a4a;
            border-radius: 10px; color: #fff; font-size: 15px;
        }
        .topic-input input:focus { outline: none; border-color: #4cc9f0; }
        .topic-input button {
            padding: 12px 24px; background: #4cc9f0; color: #000;
            border: none; border-radius: 10px; font-weight: bold; cursor: pointer;
        }
        .topic-input button:hover { background: #3aa8d8; }
        .topic-input button:disabled { background: #555; cursor: not-allowed; }
        
        /* Agent卡片 */
        .agents-grid {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
            margin-bottom: 20px;
        }
        .agent-card {
            background: #1a1a2e; border-radius: 10px; padding: 14px;
            border: 1px solid #2a2a4a; text-align: center;
        }
        .agent-card.speaking { border-color: #4cc9f0; box-shadow: 0 0 10px rgba(76,201,240,0.2); }
        .agent-card.done { border-color: #4ade80; }
        .agent-card.skipped { border-color: #666; opacity: 0.5; }
        .agent-name { font-weight: bold; font-size: 15px; margin-bottom: 4px; }
        .agent-status { font-size: 12px; color: #888; margin-bottom: 8px; }
        .agent-content {
            font-size: 13px; line-height: 1.5; color: #ccc;
            max-height: 200px; overflow-y: auto; text-align: left;
        }
        .agent-satisfied { font-size: 11px; color: #4ade80; margin-top: 6px; }
        
        /* 讨论历史 */
        .history-panel {
            background: #1a1a2e; border-radius: 10px; padding: 16px;
            border: 1px solid #2a2a4a; max-height: 400px; overflow-y: auto;
        }
        .history-msg {
            margin-bottom: 10px; padding: 8px 12px;
            border-radius: 8px; background: #0a0a1a;
        }
        .history-msg .msg-header { font-size: 12px; color: #888; margin-bottom: 4px; }
        .history-msg .msg-agent { font-weight: bold; color: #4cc9f0; }
        .history-msg .msg-content { font-size: 13px; line-height: 1.5; color: #ddd; }
        .round-marker {
            text-align: center; color: #4cc9f0; font-size: 12px;
            margin: 12px 0; opacity: 0.6;
        }
        .consensus-banner {
            text-align: center; padding: 12px; margin: 12px 0;
            background: #4ade80; color: #000; border-radius: 8px; font-weight: bold;
        }
        .ceo-summary {
            background: #1a1a2e; border: 2px solid #f72585; border-radius: 10px;
            padding: 16px; margin: 12px 0;
        }
        .ceo-summary .summary-label { color: #f72585; font-weight: bold; margin-bottom: 8px; }
        .ceo-summary .summary-content { color: #ddd; line-height: 1.6; font-size: 14px; }
        
        /* 历史记录页 */
        .history-list {
            max-width: 900px; margin: 20px auto; padding: 0 20px;
        }
        .history-item {
            background: #1a1a2e; border-radius: 10px; padding: 14px;
            border: 1px solid #2a2a4a; margin-bottom: 10px; cursor: pointer;
        }
        .history-item:hover { border-color: #4cc9f0; }
        .history-item .hi-topic { font-weight: bold; margin-bottom: 4px; }
        .history-item .hi-meta { font-size: 12px; color: #888; }
        
        /* Tab切换 */
        .tabs {
            display: flex; gap: 0; margin-bottom: 20px;
            border-bottom: 1px solid #2a2a4a;
        }
        .tab {
            padding: 10px 20px; cursor: pointer; color: #888;
            border-bottom: 2px solid transparent;
        }
        .tab.active { color: #4cc9f0; border-bottom-color: #4cc9f0; }
    </style>
</head>
<body>

<!-- 认证页面 -->
<div id="authPage" class="auth-page">
    <div class="auth-card">
        <!-- 登录 -->
        <div id="loginForm">
            <h2>AI_OS</h2>
            <p class="subtitle">多Agent协作系统</p>
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" id="loginEmail" placeholder="your@email.com">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="loginPassword" placeholder="至少6位">
            </div>
            <button class="auth-btn" onclick="doLogin()">登录</button>
            <div class="auth-switch">
                还没有账号？<a onclick="showRegister()">立即注册</a>
            </div>
            <div id="loginError" class="auth-error"></div>
        </div>
        
<!-- 注册表单 -->
        <div id="registerForm" style="display:none">
            <h2>注册 AI_OS</h2>
            <p class="subtitle">注册送5次免费讨论额度</p>
            
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" id="regEmail" placeholder="your@email.com">
            </div>
            
            <div class="form-group">
                <label>验证码</label>
                <div style="display:flex;gap:8px;align-items:center">
                    <input type="text" id="regCode" placeholder="6位验证码" maxlength="6" style="flex:1">
                    <button id="sendCodeBtn" type="button" style="padding:10px 16px;font-size:13px;background:#4cc9f0;color:#000;border:none;border-radius:8px;cursor:pointer;white-space:nowrap" onclick="sendCode()">发送验证码</button>
                </div>
            </div>
            
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="regPassword" placeholder="至少6位">
            </div>
            
            <div class="form-group">
                <label>姓名</label>
                <input type="text" id="regName" placeholder="你的名字">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>公司</label>
                    <input type="text" id="regCompany" placeholder="公司名称">
                </div>
                <div class="form-group">
                    <label>职位</label>
                    <input type="text" id="regTitle" placeholder="你的职位">
                </div>
            </div>
            
            <button class="auth-btn" onclick="doRegister()">注册</button>
            <div class="auth-switch">
                已有账号？<a onclick="showLogin()">去登录</a>
            </div>
            <div id="regError" class="auth-error"></div>
        </div>
    </div>
</div>

<!-- 主页面 -->
<div id="mainPage" class="main-page">
    <div class="navbar">
        <div class="brand">AI_OS</div>
        <div class="user-info">
            <span id="userName"></span>
            <span class="credits" id="userCredits">5次</span>
            <button class="logout-btn" onclick="doLogout()">登出</button>
        </div>
    </div>
    
    <div class="discussion-area">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('discuss')">讨论</div>
            <div class="tab" onclick="switchTab('history')">历史</div>
        </div>
        
        <!-- 讨论Tab -->
        <div id="discussTab">
            <div class="topic-input">
                <input type="text" id="topicInput" placeholder="输入讨论议题...">
                <button id="startBtn" onclick="startDiscussion()">开始讨论</button>
            </div>
            
            <div class="agents-grid" id="agentsGrid">
                <div class="agent-card" id="card-CEO">
                    <div class="agent-name">CEO</div>
                    <div class="agent-status">等待中</div>
                    <div class="agent-content"></div>
                </div>
                <div class="agent-card" id="card-CFO">
                    <div class="agent-name">CFO</div>
                    <div class="agent-status">等待中</div>
                    <div class="agent-content"></div>
                </div>
                <div class="agent-card" id="card-CTO">
                    <div class="agent-name">CTO</div>
                    <div class="agent-status">等待中</div>
                    <div class="agent-content"></div>
                </div>
                <div class="agent-card" id="card-CMO">
                    <div class="agent-name">CMO</div>
                    <div class="agent-status">等待中</div>
                    <div class="agent-content"></div>
                </div>
            </div>
            
            <div class="history-panel" id="historyPanel">
                <div style="text-align:center;color:#666;padding:20px">
                    输入议题开始讨论
                </div>
            </div>
        </div>
        
        <!-- 历史Tab -->
        <div id="historyTab" style="display:none">
            <div class="history-list" id="historyList">
                <div style="text-align:center;color:#666;padding:20px">加载中...</div>
            </div>
        </div>
    </div>
</div>

<script>
// 全局状态
let authToken = localStorage.getItem('aios_token') || null;
let currentSessionKey = null;
let lastIndex = 0;
let pollTimer = null;

// 页面初始化
window.onload = function() {
    if (authToken) {
        checkAuth();
    } else {
        showAuthPage();
    }
};

// ========== 认证 ==========

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
}

function showAuthPage() {
    document.getElementById('authPage').style.display = 'flex';
    document.getElementById('mainPage').classList.remove('active');
}

function showMainPage() {
    document.getElementById('authPage').style.display = 'none';
    document.getElementById('mainPage').classList.add('active');
}

async function checkAuth() {
    try {
        const resp = await fetch('/api/user/info', {
            headers: {'Authorization': 'Bearer ' + authToken}
        });
        if (resp.ok) {
            const data = await resp.json();
            document.getElementById('userName').textContent = data.name || data.email;
            document.getElementById('userCredits').textContent = data.credits + '次';
            showMainPage();
        } else {
            authToken = null;
            localStorage.removeItem('aios_token');
            showAuthPage();
        }
    } catch {
        showAuthPage();
    }
}

async function doLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errEl = document.getElementById('loginError');
    errEl.textContent = '';
    
    try {
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, password})
        });
        const data = await resp.json();
        
        if (resp.ok) {
            authToken = data.token;
            localStorage.setItem('aios_token', authToken);
            document.getElementById('userName').textContent = data.user.name || data.user.email;
            document.getElementById('userCredits').textContent = data.user.credits + '次';
            showMainPage();
        } else {
            errEl.textContent = data.error;
        }
    } catch(e) {
        errEl.textContent = '网络错误';
    }
}

let codeCooldown = 0;
function sendCode() {
    const email = document.getElementById('regEmail').value.trim();
    const errEl = document.getElementById('regError');
    errEl.textContent = '';
    
    if (!email) {
        errEl.textContent = '请先输入邮箱';
        return;
    }
    
    if (codeCooldown > 0) {
        errEl.textContent = '请等待 ' + codeCooldown + ' 秒后再试';
        return;
    }
    
    // 发送验证码
    fetch('/api/send-code', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email})
    })
    .then(r => r.json())
    .then(data => {
        if (data.message) {
            errEl.style.color = '#4cc9f0';
            errEl.textContent = '验证码已发送，请查收邮件';
            setTimeout(() => { errEl.style.color = '#f72585'; }, 2000);
            
            // 60秒冷却
            codeCooldown = 60;
            const btn = document.getElementById('sendCodeBtn');
            const origText = btn.textContent;
            const timer = setInterval(() => {
                codeCooldown--;
                btn.textContent = codeCooldown + 's';
                if (codeCooldown <= 0) {
                    clearInterval(timer);
                    btn.textContent = origText;
                }
            }, 1000);
        } else {
            errEl.textContent = data.error || '发送失败';
        }
    })
    .catch(() => {
        errEl.textContent = '网络错误';
    });
}

async function doRegister() {
    const email = document.getElementById('regEmail').value.trim();
    const code = document.getElementById('regCode').value.trim();
    const password = document.getElementById('regPassword').value.trim();
    const name = document.getElementById('regName').value.trim();
    const company = document.getElementById('regCompany').value.trim();
    const title = document.getElementById('regTitle').value.trim();
    const errEl = document.getElementById('regError');
    errEl.textContent = '';
    
    try {
        const resp = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email, code, password, name, company, title})
        });
        const data = await resp.json();
        
        if (resp.ok) {
            authToken = data.token;
            localStorage.setItem('aios_token', authToken);
            document.getElementById('userName').textContent = data.user.name || data.user.email;
            document.getElementById('userCredits').textContent = data.user.credits + '次';
            showMainPage();
        } else {
            errEl.textContent = data.error;
        }
    } catch(e) {
        errEl.textContent = '网络错误';
    }
}

function doLogout() {
    fetch('/api/logout', {
        method: 'POST',
        headers: {'Authorization': 'Bearer ' + authToken}
    });
    authToken = null;
    localStorage.removeItem('aios_token');
    showAuthPage();
}

// ========== Tab切换 ==========

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', (tab === 'discuss' && i === 0) || (tab === 'history' && i === 1));
    });
    document.getElementById('discussTab').style.display = tab === 'discuss' ? 'block' : 'none';
    document.getElementById('historyTab').style.display = tab === 'history' ? 'block' : 'none';
    
    if (tab === 'history') {
        loadHistory();
    }
}

// ========== 讨论 ==========

let pendingTopic = '';  // 保存待补充信息的主题

async function startDiscussion() {
    const topic = document.getElementById('topicInput').value.trim();
    if (!topic) return;
    
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.textContent = '检查中...';
    
    // 重置UI
    resetDiscussionUI();
    
    try {
        const resp = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + authToken
            },
            body: JSON.stringify({topic})
        });
        const data = await resp.json();
        
        if (resp.ok) {
            // ===== 方案B：检查是否需要交互 =====
            if (data.status === 'need_input') {
                // 显示交互表单
                pendingTopic = topic;
                showInputForm(data.questions, data.prompt);
                btn.disabled = false;
                btn.textContent = '开始讨论';
            } else {
                // 直接开始讨论
                currentSessionKey = data.session_key;
                document.getElementById('userCredits').textContent = data.credits_remaining + '次';
                lastIndex = 0;
                pollEvents();
            }
        } else {
            alert(data.error);
            btn.disabled = false;
            btn.textContent = '开始讨论';
        }
    } catch(e) {
        alert('网络错误');
        btn.disabled = false;
        btn.textContent = '开始讨论';
    }
}

function showInputForm(questions, prompt) {
    // 创建交互表单
    const formHtml = `
        <div id="inputFormModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:9999;">
            <div style="background:#1a1a2e;padding:32px;border-radius:16px;max-width:500px;width:90%;border:1px solid #2a2a4a;">
                <h3 style="color:#4cc9f0;margin-bottom:16px;">需要补充信息</h3>
                <p style="color:#aaa;font-size:14px;margin-bottom:20px;">${prompt}</p>
                <textarea id="userInputArea" style="width:100%;height:120px;background:#0a0a1a;border:1px solid #2a2a4a;border-radius:8px;color:#fff;padding:12px;font-size:14px;resize:none;" placeholder="请回答以上问题，或直接说「继续」跳过..."></textarea>
                <div style="display:flex;gap:12px;margin-top:20px;">
                    <button onclick="submitUserInput()" style="flex:1;padding:12px;background:#4cc9f0;color:#000;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">提交并继续</button>
                    <button onclick="skipInput()" style="flex:1;padding:12px;background:#333;color:#fff;border:none;border-radius:8px;cursor:pointer;">跳过</button>
                    <button onclick="closeInputForm()" style="padding:12px 20px;background:none;border:1px solid #666;color:#aaa;border-radius:8px;cursor:pointer;">取消</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', formHtml);
}

function closeInputForm() {
    const modal = document.getElementById('inputFormModal');
    if (modal) modal.remove();
    pendingTopic = '';
}

async function submitUserInput() {
    const userInput = document.getElementById('userInputArea').value.trim();
    if (!userInput) {
        alert('请回答问题或点击跳过');
        return;
    }
    
    // 先保存主题，再关闭表单
    const topic = pendingTopic;
    closeInputForm();
    
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.textContent = '讨论中...';
    
    try {
        const resp = await fetch('/api/continue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + authToken
            },
            body: JSON.stringify({
                topic: topic,
                user_input: userInput
            })
        });
        const data = await resp.json();
        
        if (resp.ok) {
            currentSessionKey = data.session_key;
            document.getElementById('userCredits').textContent = data.credits_remaining + '次';
            lastIndex = 0;
            pollEvents();
        } else {
            alert(data.error);
            btn.disabled = false;
            btn.textContent = '开始讨论';
        }
    } catch(e) {
        alert('网络错误');
        btn.disabled = false;
        btn.textContent = '开始讨论';
    }
}

function skipInput() {
    document.getElementById('userInputArea').value = '继续';
    submitUserInput();
}

function resetDiscussionUI() {
    ['CEO','CFO','CTO','CMO'].forEach(agent => {
        const card = document.getElementById('card-' + agent);
        card.className = 'agent-card';
        card.querySelector('.agent-status').textContent = '等待中';
        card.querySelector('.agent-content').textContent = '';
    });
    document.getElementById('historyPanel').innerHTML = '';
}

function pollEvents() {
    if (!currentSessionKey) return;
    
    fetch('/api/events?session_key=' + currentSessionKey + '&last=' + lastIndex, {
        headers: {'Authorization': 'Bearer ' + authToken}
    })
    .then(r => r.json())
    .then(data => {
        // 处理事件
        data.events.forEach(event => processEvent(event));
        lastIndex += data.events.length;
        
        // 更新额度
        if (data.credits !== undefined) {
            document.getElementById('userCredits').textContent = data.credits + '次';
        }
        
        // 继续轮询
        if (data.running) {
            setTimeout(pollEvents, 500);
        } else {
            const btn = document.getElementById('startBtn');
            btn.disabled = false;
            btn.textContent = '开始讨论';
        }
    })
    .catch(() => {
        setTimeout(pollEvents, 1000);
    });
}

function processEvent(event) {
    const type = event.type;
    
    if (type === 'round_start') {
        addRoundMarker(event.data ? event.data.round : event.round);
    }
    else if (type === 'agent_start') {
        const agent = event.data ? event.data.agent : event.agent;
        const card = document.getElementById('card-' + agent);
        if (card) {
            card.className = 'agent-card speaking';
            card.querySelector('.agent-status').textContent = '发言中...';
        }
    }
    else if (type === 'agent_done') {
        const d = event.data || event;
        const agent = d.agent;
        const content = d.content || '';
        const satisfied = d.satisfied;
        const skipped = d.skipped;
        
        const card = document.getElementById('card-' + agent);
        if (card) {
            card.className = 'agent-card' + (skipped ? ' skipped' : ' done');
            card.querySelector('.agent-status').textContent = skipped ? '跳过' : '完成';
            card.querySelector('.agent-content').textContent = content;
        }
        
        addHistoryMessage(agent, content, satisfied, skipped, event.time);
    }
    else if (type === 'ceo_summary') {
        const content = event.data ? event.data.content : event.content;
        addCEOSummary(content, event.time);
    }
    else if (type === 'consensus') {
        showConsensusBanner();
    }
    else if (type === 'end') {
        // 讨论结束
    }
}

function addRoundMarker(round) {
    const panel = document.getElementById('historyPanel');
    const marker = document.createElement('div');
    marker.className = 'round-marker';
    marker.textContent = '━━━ Round ' + round + ' ━━━';
    panel.appendChild(marker);
    panel.scrollTop = panel.scrollHeight;
}

function addHistoryMessage(agent, content, satisfied, skipped, time) {
    const panel = document.getElementById('historyPanel');
    const msg = document.createElement('div');
    msg.className = 'history-msg';
    
    const status = skipped ? '（跳过）' : (satisfied ? '（满意）' : '');
    msg.innerHTML = '<div class="msg-header"><span class="msg-agent">' + agent + '</span> ' + status + ' ' + (time || '') + '</div>' +
                    '<div class="msg-content">' + content + '</div>';
    panel.appendChild(msg);
    panel.scrollTop = panel.scrollHeight;
}

function addCEOSummary(content, time) {
    const panel = document.getElementById('historyPanel');
    const div = document.createElement('div');
    div.className = 'ceo-summary';
    div.innerHTML = '<div class="summary-label">CEO总结 ' + (time || '') + '</div>' +
                    '<div class="summary-content">' + content + '</div>';
    panel.appendChild(div);
    panel.scrollTop = panel.scrollHeight;
}

function showConsensusBanner() {
    const panel = document.getElementById('historyPanel');
    const banner = document.createElement('div');
    banner.className = 'consensus-banner';
    banner.textContent = '✓ 达成共识！';
    panel.appendChild(banner);
    panel.scrollTop = panel.scrollHeight;
}

// ========== 历史 ==========

async function loadHistory() {
    try {
        const resp = await fetch('/api/history', {
            headers: {'Authorization': 'Bearer ' + authToken}
        });
        const data = await resp.json();
        
        const list = document.getElementById('historyList');
        if (!data.discussions || data.discussions.length === 0) {
            list.innerHTML = '<div style="text-align:center;color:#666;padding:20px">暂无讨论记录</div>';
            return;
        }
        
        list.innerHTML = data.discussions.map(d => 
            '<div class="history-item" onclick="viewDetail(' + d.id + ')">' +
            '<div class="hi-topic">' + d.topic + '</div>' +
            '<div class="hi-meta">' + d.rounds + '轮 | ' + (d.consensus ? '达成共识' : '未达成') + ' | ' + d.created_at + '</div>' +
            '</div>'
        ).join('');
    } catch(e) {
        document.getElementById('historyList').innerHTML = '<div style="color:#f72585">加载失败</div>';
    }
}

async function viewDetail(id) {
    try {
        const resp = await fetch('/api/history/' + id, {
            headers: {'Authorization': 'Bearer ' + authToken}
        });
        const detail = await resp.json();
        
        // 切换到讨论tab显示详情
        switchTab('discuss');
        resetDiscussionUI();
        
        const panel = document.getElementById('historyPanel');
        panel.innerHTML = '<div style="color:#4cc9f0;font-weight:bold;margin-bottom:12px">历史讨论: ' + detail.topic + '</div>';
        
        if (detail.messages) {
            detail.messages.forEach(msg => {
                if (msg.round && msg.round !== '总结') {
                    addRoundMarker(msg.round);
                }
                addHistoryMessage(msg.agent, msg.content, msg.satisfied, msg.skipped, '');
            });
        }
    } catch(e) {
        alert('加载失败');
    }
}
</script>
</body>
</html>
"""


def run_web_server(port=8765):
    """启动Web服务器"""
    init_db()
    print(f"AI_OS Web界面启动: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    run_web_server()