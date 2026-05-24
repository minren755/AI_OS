"""
讨论监控面板

启动一个简单的HTTP服务器，提供实时讨论进度可视化
"""
import json
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class DiscussionMonitor:
    """讨论进度监控器"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.state = {
            "topic": "",
            "round": 0,
            "agents": {
                "CEO": {"status": "等待中", "content": "", "satisfied": False},
                "CFO": {"status": "等待中", "content": "", "satisfied": False},
                "CTO": {"status": "等待中", "content": "", "satisfied": False},
                "CMO": {"status": "等待中", "content": "", "satisfied": False},
            },
            "consensus": False,
            "history": [],
            "start_time": None,
        }
        self.running = False
        self._server = None
        self._thread = None
    
    def update(self, event: dict):
        """更新监控状态"""
        event_type = event.get("type", "")
        
        if event_type == "start":
            self.state["topic"] = event.get("topic", "")
            self.state["start_time"] = datetime.now().strftime("%H:%M:%S")
            self.state["round"] = 1
            for agent in self.state["agents"]:
                self.state["agents"][agent]["status"] = "等待中"
        
        elif event_type == "agent_start":
            agent = event.get("agent", "")
            self.state["agents"][agent]["status"] = "发言中"
        
        elif event_type == "agent_done":
            agent = event.get("agent", "")
            content = event.get("content", "")[:100]
            satisfied = event.get("satisfied", False)
            skipped = event.get("skipped", False)
            
            self.state["agents"][agent]["status"] = "完成" if not skipped else "跳过"
            self.state["agents"][agent]["content"] = content
            self.state["agents"][agent]["satisfied"] = satisfied
            
            # 添加到历史
            self.state["history"].append({
                "round": self.state["round"],
                "agent": agent,
                "content": content,
                "time": datetime.now().strftime("%H:%M:%S")
            })
        
        elif event_type == "round_done":
            self.state["round"] += 1
        
        elif event_type == "consensus":
            self.state["consensus"] = True
        
        # 写入状态文件（供前端轮询）
        self._write_state()
    
    def _write_state(self):
        """写入状态文件"""
        state_file = Path("/tmp/ai_os_monitor.json")
        with open(state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def run_dashboard(self):
        """运行监控面板"""
        self.running = True
        
        # 生成HTML页面
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI_OS 讨论监控</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .topic { font-size: 24px; color: #4ecdc4; }
        .round { color: #f39c12; }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .agent-card { 
            background: #16213e; border-radius: 12px; padding: 20px;
            border-left: 4px solid #666;
        }
        .agent-card.speaking { border-color: #f39c12; animation: pulse 1s infinite; }
        .agent-card.done { border-color: #27ae60; }
        .agent-card.skipped { border-color: #666; opacity: 0.6; }
        .agent-card.satisfied { border-color: #4ecdc4; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(243,156,18,0.4); } 100% { box-shadow: 0 0 0 10px rgba(243,156,18,0); } }
        .agent-name { font-size: 18px; font-weight: bold; margin-bottom: 8px; }
        .agent-status { font-size: 14px; color: #888; }
        .agent-content { margin-top: 10px; font-size: 13px; line-height: 1.4; color: #ccc; }
        .history { margin-top: 30px; background: #16213e; border-radius: 12px; padding: 20px; }
        .history-title { font-size: 16px; color: #4ecdc4; margin-bottom: 10px; }
        .history-item { padding: 8px 0; border-bottom: 1px solid #333; }
        .consensus { text-align: center; padding: 20px; background: #27ae60; color: white; border-radius: 12px; margin-top: 20px; font-size: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="topic" id="topic">等待讨论开始...</div>
        <div class="round" id="round"></div>
    </div>
    
    <div class="grid" id="agents"></div>
    
    <div class="history" id="history" style="display:none;">
        <div class="history-title">📝 讨论记录</div>
        <div id="history-list"></div>
    </div>
    
    <div id="consensus-box" style="display:none;">
        <div class="consensus">✅ 达成共识</div>
    </div>

    <script>
        const agentOrder = ['CEO', 'CFO', 'CTO', 'CMO'];
        
        function render() {
            fetch('/state')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('topic').textContent = data.topic || '等待讨论开始...';
                    document.getElementById('round').textContent = data.round > 0 ? `Round ${data.round}` : '';
                    
                    // Agent cards
                    const agentsDiv = document.getElementById('agents');
                    agentsDiv.innerHTML = '';
                    
                    agentOrder.forEach(agent => {
                        const info = data.agents[agent] || {};
                        const status = info.status || '等待中';
                        const cardClass = status === '发言中' ? 'speaking' : 
                                          status === '跳过' ? 'skipped' :
                                          info.satisfied ? 'satisfied' :
                                          status === '完成' ? 'done' : '';
                        
                        const card = document.createElement('div');
                        card.className = `agent-card ${cardClass}`;
                        card.innerHTML = `
                            <div class="agent-name">${agent} ${info.satisfied ? '✓' : ''}</div>
                            <div class="agent-status">${status}</div>
                            <div class="agent-content">${info.content || ''}</div>
                        `;
                        agentsDiv.appendChild(card);
                    });
                    
                    // History
                    if (data.history.length > 0) {
                        document.getElementById('history').style.display = 'block';
                        const historyList = document.getElementById('history-list');
                        historyList.innerHTML = data.history.slice(-10).map(h => 
                            `<div class="history-item">
                                <strong>[${h.time}] ${h.agent}:</strong> ${h.content}
                            </div>`
                        ).join('');
                    }
                    
                    // Consensus
                    if (data.consensus) {
                        document.getElementById('consensus-box').style.display = 'block';
                    }
                })
                .catch(e => console.log('Polling...'));
        }
        
        setInterval(render, 1000);
        render();
    </script>
</body>
</html>'''
        
        # 保存HTML
        monitor_dir = Path("/tmp/ai_os_monitor")
        monitor_dir.mkdir(exist_ok=True)
        (monitor_dir / "index.html").write_text(html_content)
        
        # 状态API处理器
        class MonitorHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(monitor_dir), **kwargs)
            
            def do_GET(self):
                if self.path == '/state':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    state_file = Path("/tmp/ai_os_monitor.json")
                    if state_file.exists():
                        self.wfile.write(state_file.read_bytes())
                    else:
                        self.wfile.write(b'{}')
                else:
                    super().do_GET()
        
        # 启动HTTP服务器（允许端口复用）
        import socket
        import socketserver
        
        class ReusableHTTPServer(HTTPServer):
            allow_reuse_address = True
            allow_reuse_port = True
        
        self._server = ReusableHTTPServer(('localhost', self.port), MonitorHandler)
        print(f"监控面板: http://localhost:{self.port}")
        
        try:
            while self.running:
                self._server.handle_request()
        except Exception:
            pass
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self._server:
            self._server.shutdown()


# 修改DiscussionEngine以支持监控回调
def add_monitor_support():
    """给DiscussionEngine添加监控回调支持"""
    from src.discussion.engine import DiscussionEngine
    
    original_run_round = DiscussionEngine._run_round
    
    async def monitored_run_round(self, speakers, topic, round_num):
        if hasattr(self, 'on_message') and self.on_message:
            self.on_message({"type": "start", "topic": topic})
        
        for speaker in speakers:
            if hasattr(self, 'on_message') and self.on_message:
                self.on_message({"type": "agent_start", "agent": speaker})
            
            result = await self._call_llm_original(speaker, self._build_prompt(speaker, topic, round_num))
            parsed = self._parse_response(result)
            
            if hasattr(self, 'on_message') and self.on_message:
                self.on_message({
                    "type": "agent_done",
                    "agent": speaker,
                    "content": parsed.content,
                    "satisfied": parsed.satisfied,
                    "skipped": parsed.skipped
                })
    
    DiscussionEngine._run_round = monitored_run_round
