"""AI_OS Web界面 - 带用户系统"""import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, render_template

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import (init_db, create_user, get_user_by_email, get_user_by_id,
    get_credits, use_credit, save_discussion, save_message,
    get_user_discussions, get_discussion_detail, update_last_login)
from src.auth.auth import (hash_password, verify_password, create_session,
    get_user_from_session, delete_session)
from src.discussion.engine import DiscussionEngine, DiscussionConfig

app = Flask(__name__, template_folder='templates')
app.secret_key = "ai_os_secret_key"current_discussions = {}def require_auth(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_id = get_user_from_session(token)
        if not user_id:
            return jsonify({"error": "请先登录"}), 401        request.user_id = user_id
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/app")
def main_app():
    return render_template_string(HTML_TEMPLATE)

# API routes continue...
