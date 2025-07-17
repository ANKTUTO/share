#!/usr/bin/env python3
"""
Unified Screen Sharing Server - WebContainer Compatible
A simple HTTP server for screen sharing that works in WebContainer environments
"""

import http.server
import socketserver
import json
import threading
import time
import base64
import io
import os
from urllib.parse import urlparse, parse_qs
from http import HTTPStatus

try:
    import mss
    import numpy as np
    from PIL import Image
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

class ScreenShareHandler(http.server.SimpleHTTPRequestHandler):
    # Class variables to store shared state
    users = {}
    current_presenter = None
    chat_messages = []
    settings = {
        'fps': 30,
        'quality': 85,
        'monitor': 0
    }
    current_frame = None
    frame_lock = threading.Lock()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Serve the main page
        if path == '/' or path == '/index.html':
            self.serve_main_page()
        elif path == '/api/users':
            self.serve_users()
        elif path == '/api/messages':
            self.serve_messages()
        elif path == '/api/frame':
            self.serve_frame()
        elif path == '/api/settings':
            self.serve_settings()
        elif path == '/api/status':
            self.serve_status()
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except json.JSONDecodeError:
            data = {}
        
        if path == '/api/join':
            self.handle_join(data)
        elif path == '/api/message':
            self.handle_message(data)
        elif path == '/api/request_presenter':
            self.handle_request_presenter(data)
        elif path == '/api/start_sharing':
            self.handle_start_sharing(data)
        elif path == '/api/stop_sharing':
            self.handle_stop_sharing(data)
        elif path == '/api/settings':
            self.handle_settings_update(data)
        else:
            self.send_error(404)
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def serve_main_page(self):
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Screen Share Pro - Multi-User Edition</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            color: #4a5568;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .status-item {
            background: #f7fafc;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            border: 1px solid #e2e8f0;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
        }
        
        .video-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .video-container {
            position: relative;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .video-placeholder {
            color: #666;
            font-size: 18px;
            text-align: center;
        }
        
        #screenFrame {
            max-width: 100%;
            max-height: 500px;
            border-radius: 10px;
        }
        
        .controls {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
            font-size: 14px;
        }
        
        .btn-primary {
            background: #4299e1;
            color: white;
        }
        
        .btn-primary:hover {
            background: #3182ce;
        }
        
        .btn-danger {
            background: #f56565;
            color: white;
        }
        
        .btn-danger:hover {
            background: #e53e3e;
        }
        
        .btn-secondary {
            background: #718096;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #4a5568;
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .panel {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .panel h3 {
            margin-bottom: 15px;
            color: #4a5568;
            font-size: 16px;
        }
        
        .user-list {
            list-style: none;
        }
        
        .user-item {
            padding: 8px 12px;
            margin-bottom: 5px;
            background: #f7fafc;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
        }
        
        .user-role {
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 4px;
            background: #e2e8f0;
            color: #4a5568;
        }
        
        .user-role.presenter {
            background: #48bb78;
            color: white;
        }
        
        .chat-messages {
            height: 200px;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            background: #f7fafc;
        }
        
        .message {
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .message-user {
            font-weight: 600;
            color: #4299e1;
        }
        
        .chat-input {
            display: flex;
            gap: 8px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .settings-grid {
            display: grid;
            gap: 10px;
        }
        
        .setting-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .setting-item label {
            font-size: 12px;
            font-weight: 500;
            color: #4a5568;
        }
        
        .setting-item input,
        .setting-item select {
            padding: 6px 8px;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            font-size: 14px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
            
            .controls {
                justify-content: center;
            }
        }
        
        .fullscreen-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border: none;
            padding: 8px;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Screen Share Pro - Multi-User Edition</h1>
            <div class="status">
                <div class="status-item">
                    <strong>Status:</strong> <span id="connectionStatus">Connecting...</span>
                </div>
                <div class="status-item">
                    <strong>Role:</strong> <span id="userRole">Viewer</span>
                </div>
                <div class="status-item">
                    <strong>Users:</strong> <span id="userCount">0</span>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="video-section">
                <div class="video-container" id="videoContainer">
                    <div class="video-placeholder" id="placeholder">
                        No screen being shared
                    </div>
                    <img id="screenFrame" style="display: none;" alt="Shared Screen">
                    <button class="fullscreen-btn" id="fullscreenBtn" style="display: none;">⛶</button>
                </div>
                
                <div class="controls">
                    <button class="btn btn-primary" id="startBtn" disabled>Start Sharing</button>
                    <button class="btn btn-danger" id="stopBtn" disabled style="display: none;">Stop Sharing</button>
                    <button class="btn btn-secondary" id="requestBtn">Request Presenter</button>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="panel">
                    <h3>👥 Participants</h3>
                    <ul class="user-list" id="userList"></ul>
                </div>
                
                <div class="panel">
                    <h3>💬 Chat</h3>
                    <div class="chat-messages" id="chatMessages"></div>
                    <div class="chat-input">
                        <input type="text" id="messageInput" placeholder="Type a message..." maxlength="200">
                        <button class="btn btn-primary" id="sendBtn">Send</button>
                    </div>
                </div>
                
                <div class="panel">
                    <h3>⚙️ Settings</h3>
                    <div class="settings-grid">
                        <div class="setting-item">
                            <label>FPS</label>
                            <select id="fpsSelect">
                                <option value="15">15 FPS</option>
                                <option value="30" selected>30 FPS</option>
                                <option value="60">60 FPS</option>
                            </select>
                        </div>
                        <div class="setting-item">
                            <label>Quality</label>
                            <input type="range" id="qualitySlider" min="50" max="95" value="85">
                            <span id="qualityValue">85%</span>
                        </div>
                        <div class="setting-item">
                            <label>Monitor</label>
                            <select id="monitorSelect">
                                <option value="0">Primary Monitor</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        class ScreenShareClient {
            constructor() {
                this.userId = 'user_' + Math.random().toString(36).substr(2, 9);
                this.isPresenter = false;
                this.isSharing = false;
                this.frameInterval = null;
                
                this.initializeElements();
                this.setupEventListeners();
                this.joinRoom();
                this.startPolling();
            }
            
            initializeElements() {
                this.elements = {
                    connectionStatus: document.getElementById('connectionStatus'),
                    userRole: document.getElementById('userRole'),
                    userCount: document.getElementById('userCount'),
                    videoContainer: document.getElementById('videoContainer'),
                    placeholder: document.getElementById('placeholder'),
                    screenFrame: document.getElementById('screenFrame'),
                    fullscreenBtn: document.getElementById('fullscreenBtn'),
                    startBtn: document.getElementById('startBtn'),
                    stopBtn: document.getElementById('stopBtn'),
                    requestBtn: document.getElementById('requestBtn'),
                    userList: document.getElementById('userList'),
                    chatMessages: document.getElementById('chatMessages'),
                    messageInput: document.getElementById('messageInput'),
                    sendBtn: document.getElementById('sendBtn'),
                    fpsSelect: document.getElementById('fpsSelect'),
                    qualitySlider: document.getElementById('qualitySlider'),
                    qualityValue: document.getElementById('qualityValue'),
                    monitorSelect: document.getElementById('monitorSelect')
                };
            }
            
            setupEventListeners() {
                this.elements.startBtn.addEventListener('click', () => this.startSharing());
                this.elements.stopBtn.addEventListener('click', () => this.stopSharing());
                this.elements.requestBtn.addEventListener('click', () => this.requestPresenter());
                this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
                this.elements.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
                
                this.elements.messageInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') this.sendMessage();
                });
                
                this.elements.qualitySlider.addEventListener('input', (e) => {
                    this.elements.qualityValue.textContent = e.target.value + '%';
                    this.updateSettings();
                });
                
                this.elements.fpsSelect.addEventListener('change', () => this.updateSettings());
                this.elements.monitorSelect.addEventListener('change', () => this.updateSettings());
            }
            
            async joinRoom() {
                try {
                    const response = await fetch('/api/join', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userId: this.userId, name: `User ${this.userId.slice(-4)}` })
                    });
                    
                    if (response.ok) {
                        this.elements.connectionStatus.textContent = 'Connected';
                        this.elements.connectionStatus.style.color = '#48bb78';
                    }
                } catch (error) {
                    console.error('Failed to join room:', error);
                    this.elements.connectionStatus.textContent = 'Connection Failed';
                    this.elements.connectionStatus.style.color = '#f56565';
                }
            }
            
            startPolling() {
                // Poll for updates every 1000ms
                setInterval(() => {
                    this.updateUsers();
                    this.updateMessages();
                    this.updateStatus();
                }, 1000);
                
                // Poll for frames every 100ms when sharing is active
                setInterval(() => {
                    this.updateFrame();
                }, 100);
            }
            
            async updateUsers() {
                try {
                    const response = await fetch('/api/users');
                    const data = await response.json();
                    
                    this.elements.userCount.textContent = Object.keys(data.users).length;
                    this.updateUserList(data.users, data.presenter);
                    
                    this.isPresenter = data.presenter === this.userId;
                    this.elements.userRole.textContent = this.isPresenter ? 'Presenter' : 'Viewer';
                    this.elements.startBtn.disabled = !this.isPresenter;
                    this.elements.requestBtn.disabled = this.isPresenter;
                } catch (error) {
                    console.error('Failed to update users:', error);
                }
            }
            
            updateUserList(users, presenter) {
                const userList = this.elements.userList;
                userList.innerHTML = '';
                
                Object.entries(users).forEach(([userId, user]) => {
                    const li = document.createElement('li');
                    li.className = 'user-item';
                    
                    const isPresenter = userId === presenter;
                    li.innerHTML = `
                        <span>${user.name}</span>
                        <span class="user-role ${isPresenter ? 'presenter' : ''}">${isPresenter ? 'Presenter' : 'Viewer'}</span>
                    `;
                    
                    userList.appendChild(li);
                });
            }
            
            async updateMessages() {
                try {
                    const response = await fetch('/api/messages');
                    const data = await response.json();
                    
                    const chatMessages = this.elements.chatMessages;
                    chatMessages.innerHTML = '';
                    
                    data.messages.forEach(msg => {
                        const div = document.createElement('div');
                        div.className = 'message';
                        div.innerHTML = `<span class="message-user">${msg.user}:</span> ${msg.text}`;
                        chatMessages.appendChild(div);
                    });
                    
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                } catch (error) {
                    console.error('Failed to update messages:', error);
                }
            }
            
            async updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    this.isSharing = data.sharing;
                    this.elements.startBtn.style.display = this.isSharing ? 'none' : 'inline-block';
                    this.elements.stopBtn.style.display = this.isSharing ? 'inline-block' : 'none';
                } catch (error) {
                    console.error('Failed to update status:', error);
                }
            }
            
            async updateFrame() {
                try {
                    const response = await fetch('/api/frame');
                    if (response.ok) {
                        const blob = await response.blob();
                        if (blob.size > 0) {
                            const url = URL.createObjectURL(blob);
                            this.elements.screenFrame.src = url;
                            this.elements.screenFrame.style.display = 'block';
                            this.elements.placeholder.style.display = 'none';
                            this.elements.fullscreenBtn.style.display = 'block';
                        } else {
                            this.elements.screenFrame.style.display = 'none';
                            this.elements.placeholder.style.display = 'block';
                            this.elements.fullscreenBtn.style.display = 'none';
                        }
                    }
                } catch (error) {
                    // Silently handle frame update errors
                }
            }
            
            async startSharing() {
                try {
                    const response = await fetch('/api/start_sharing', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userId: this.userId })
                    });
                    
                    if (response.ok) {
                        console.log('Started sharing');
                    }
                } catch (error) {
                    console.error('Failed to start sharing:', error);
                }
            }
            
            async stopSharing() {
                try {
                    const response = await fetch('/api/stop_sharing', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userId: this.userId })
                    });
                    
                    if (response.ok) {
                        console.log('Stopped sharing');
                    }
                } catch (error) {
                    console.error('Failed to stop sharing:', error);
                }
            }
            
            async requestPresenter() {
                try {
                    const response = await fetch('/api/request_presenter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userId: this.userId })
                    });
                    
                    if (response.ok) {
                        console.log('Requested presenter role');
                    }
                } catch (error) {
                    console.error('Failed to request presenter:', error);
                }
            }
            
            async sendMessage() {
                const text = this.elements.messageInput.value.trim();
                if (!text) return;
                
                try {
                    const response = await fetch('/api/message', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            userId: this.userId, 
                            text: text,
                            user: `User ${this.userId.slice(-4)}`
                        })
                    });
                    
                    if (response.ok) {
                        this.elements.messageInput.value = '';
                    }
                } catch (error) {
                    console.error('Failed to send message:', error);
                }
            }
            
            async updateSettings() {
                const settings = {
                    fps: parseInt(this.elements.fpsSelect.value),
                    quality: parseInt(this.elements.qualitySlider.value),
                    monitor: parseInt(this.elements.monitorSelect.value)
                };
                
                try {
                    await fetch('/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(settings)
                    });
                } catch (error) {
                    console.error('Failed to update settings:', error);
                }
            }
            
            toggleFullscreen() {
                const container = this.elements.videoContainer;
                if (!document.fullscreenElement) {
                    container.requestFullscreen();
                } else {
                    document.exitFullscreen();
                }
            }
        }
        
        // Initialize the client when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new ScreenShareClient();
        });
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_users(self):
        self.send_json_response({
            'users': self.users,
            'presenter': self.current_presenter
        })
    
    def serve_messages(self):
        self.send_json_response({'messages': self.chat_messages})
    
    def serve_frame(self):
        with self.frame_lock:
            if self.current_frame:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(self.current_frame)
            else:
                self.send_response(204)  # No content
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
    
    def serve_settings(self):
        self.send_json_response(self.settings)
    
    def serve_status(self):
        self.send_json_response({
            'sharing': self.current_frame is not None,
            'presenter': self.current_presenter
        })
    
    def handle_join(self, data):
        user_id = data.get('userId')
        name = data.get('name', f'User {user_id[-4:]}')
        
        if user_id:
            self.users[user_id] = {'name': name, 'joined_at': time.time()}
            
            # First user becomes presenter
            if not self.current_presenter:
                self.current_presenter = user_id
        
        self.send_json_response({'success': True})
    
    def handle_message(self, data):
        user_id = data.get('userId')
        text = data.get('text', '')
        user_name = data.get('user', 'Unknown')
        
        if user_id and text:
            self.chat_messages.append({
                'user': user_name,
                'text': text,
                'timestamp': time.time()
            })
            
            # Keep only last 50 messages
            if len(self.chat_messages) > 50:
                self.chat_messages = self.chat_messages[-50:]
        
        self.send_json_response({'success': True})
    
    def handle_request_presenter(self, data):
        user_id = data.get('userId')
        
        if user_id and user_id in self.users:
            # Simple presenter assignment - first come, first served
            if not self.current_presenter or self.current_presenter not in self.users:
                self.current_presenter = user_id
        
        self.send_json_response({'success': True})
    
    def handle_start_sharing(self, data):
        user_id = data.get('userId')
        
        if user_id == self.current_presenter and MSS_AVAILABLE:
            # Start screen capture in a separate thread
            if not hasattr(self, 'capture_thread') or not self.capture_thread.is_alive():
                self.capture_thread = threading.Thread(target=self.screen_capture_loop, daemon=True)
                self.capture_thread.start()
        
        self.send_json_response({'success': True})
    
    def handle_stop_sharing(self, data):
        user_id = data.get('userId')
        
        if user_id == self.current_presenter:
            with self.frame_lock:
                self.current_frame = None
        
        self.send_json_response({'success': True})
    
    def handle_settings_update(self, data):
        self.settings.update(data)
        self.send_json_response({'success': True})
    
    def screen_capture_loop(self):
        if not MSS_AVAILABLE:
            return
            
        with mss.mss() as sct:
            while True:
                try:
                    # Check if we should still be capturing
                    if self.current_frame is None and hasattr(self, '_stop_capture'):
                        break
                    
                    # Get monitor
                    monitor = sct.monitors[self.settings.get('monitor', 1)]
                    
                    # Capture screen
                    screenshot = sct.grab(monitor)
                    
                    # Convert to PIL Image
                    img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                    
                    # Resize if needed (for performance)
                    max_width = 1280
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Convert to JPEG
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=self.settings.get('quality', 85))
                    
                    with self.frame_lock:
                        self.current_frame = buffer.getvalue()
                    
                    # Control FPS
                    time.sleep(1.0 / self.settings.get('fps', 30))
                    
                except Exception as e:
                    print(f"Screen capture error: {e}")
                    time.sleep(1)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Screen Share Pro - Multi-User Edition')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS')
    parser.add_argument('--quality', type=int, default=85, help='JPEG quality')
    
    args = parser.parse_args()
    
    # Update default settings
    ScreenShareHandler.settings.update({
        'fps': args.fps,
        'quality': args.quality
    })
    
    print(f"""
🚀 Screen Share Pro - Multi-User Edition
========================================
Server starting on: http://{args.host}:{args.port}

📋 How to test multi-user functionality:
1. Open http://localhost:{args.port} in multiple browser tabs
2. Each tab represents a different user
3. First user becomes presenter automatically
4. Test screen sharing, chat, and presenter switching

🔧 Features:
- Multi-user support (like Google Meet)
- Real-time screen sharing
- Group chat system
- Presenter role management
- Quality controls (FPS: {args.fps}, Quality: {args.quality}%)

⚠️  Note: Screen capture requires 'mss' and 'PIL' libraries
Install with: pip install -r requirements.txt
""")
    
    try:
        with socketserver.TCPServer((args.host, args.port), ScreenShareHandler) as httpd:
            print(f"✅ Server running at http://{args.host}:{args.port}")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == '__main__':
    main()