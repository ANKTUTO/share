#!/usr/bin/env python3
"""
Unified High-Performance Screen Sharing Server
Single Python interface with multi-user support like Google Meet
"""

import asyncio
import json
import logging
import time
import base64
import uuid
from pathlib import Path
from typing import Dict, Set, Optional, List
import argparse
import signal
import sys

# HTTP and WebSocket server
from aiohttp import web, WSMsgType
import aiohttp_cors

# Screen capture
try:
    import mss
    import cv2
    import numpy as np
    MSS_AVAILABLE = True
    CV2_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    MSS_AVAILABLE = False
    CV2_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScreenCapture:
    """High-performance screen capture with multiple monitor support"""
    
    def __init__(self, target_fps=60, target_resolution=(1280, 720), quality=85):
        self.target_fps = target_fps
        self.target_resolution = target_resolution
        self.quality = quality
        self.running = False
        self.current_frame = None
        self.frame_count = 0
        self.start_time = time.time()
        self.last_fps_time = time.time()
        self.actual_fps = 0
        self.monitors = []
        self.selected_monitor = 0
        
        if MSS_AVAILABLE:
            self.sct = mss.mss()
            self.monitors = self.sct.monitors[1:]  # Skip the combined monitor
            logger.info(f"Available monitors: {len(self.monitors)}")
            for i, monitor in enumerate(self.monitors):
                logger.info(f"Monitor {i}: {monitor}")
        else:
            logger.warning("MSS not available, using test pattern")
            
    def get_monitors(self):
        """Get list of available monitors"""
        if MSS_AVAILABLE:
            return [
                {
                    'id': i,
                    'name': f"Monitor {i + 1}",
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'primary': i == 0
                }
                for i, monitor in enumerate(self.monitors)
            ]
        return [{'id': 0, 'name': 'Test Monitor', 'width': 1920, 'height': 1080, 'primary': True}]
        
    def select_monitor(self, monitor_id):
        """Select which monitor to capture"""
        if 0 <= monitor_id < len(self.monitors):
            self.selected_monitor = monitor_id
            logger.info(f"Selected monitor {monitor_id}")
            return True
        return False
        
    def start_capture(self):
        """Start screen capture"""
        if self.running:
            return
            
        self.running = True
        self.capture_task = asyncio.create_task(self._capture_loop())
        logger.info(f"Screen capture started: {self.target_fps}FPS, {self.target_resolution}")
        
    async def stop_capture(self):
        """Stop screen capture"""
        self.running = False
        if hasattr(self, 'capture_task'):
            self.capture_task.cancel()
            try:
                await self.capture_task
            except asyncio.CancelledError:
                pass
        logger.info("Screen capture stopped")
        
    async def _capture_loop(self):
        """Main capture loop"""
        frame_interval = 1.0 / self.target_fps
        
        while self.running:
            start_time = time.time()
            
            try:
                if MSS_AVAILABLE and self.selected_monitor < len(self.monitors):
                    # Capture from selected monitor
                    monitor = self.monitors[self.selected_monitor]
                    screenshot = self.sct.grab(monitor)
                    
                    if CV2_AVAILABLE:
                        # Convert to numpy array
                        frame = np.array(screenshot)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                        
                        # Resize if needed
                        if frame.shape[:2][::-1] != self.target_resolution:
                            frame = cv2.resize(frame, self.target_resolution, interpolation=cv2.INTER_LINEAR)
                        
                        # Encode to JPEG
                        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), 
                                               [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                        self.current_frame = base64.b64encode(buffer).decode('utf-8')
                    else:
                        # Fallback using PIL
                        try:
                            from PIL import Image
                            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                            img = img.resize(self.target_resolution, Image.Resampling.LANCZOS)
                            
                            import io
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=self.quality)
                            self.current_frame = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        except ImportError:
                            self.current_frame = self._generate_test_frame()
                else:
                    # Generate test pattern
                    self.current_frame = self._generate_test_frame()
                    
                self.frame_count += 1
                self._update_fps()
                
            except Exception as e:
                logger.error(f"Capture error: {e}")
                self.current_frame = self._generate_test_frame()
                
            # Maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
    def _generate_test_frame(self):
        """Generate test pattern frame"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            width, height = self.target_resolution
            img = Image.new('RGB', (width, height), color='#1a1a2e')
            draw = ImageDraw.Draw(img)
            
            # Draw gradient background
            for y in range(height):
                color_val = int(26 + (y / height) * 50)
                draw.line([(0, y), (width, y)], fill=(color_val, color_val, color_val + 20))
            
            # Draw grid pattern
            grid_size = 50
            for x in range(0, width, grid_size):
                draw.line([(x, 0), (x, height)], fill='#16213e', width=1)
            for y in range(0, height, grid_size):
                draw.line([(0, y), (width, y)], fill='#16213e', width=1)
            
            # Draw center info
            center_x, center_y = width // 2, height // 2
            
            # Title
            title = "🖥️ Screen Share Demo"
            title_bbox = draw.textbbox((0, 0), title)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text((center_x - title_width // 2, center_y - 60), title, fill='white')
            
            # Frame info
            info = f"Frame: {self.frame_count} | FPS: {self.actual_fps:.1f} | Time: {time.time():.1f}"
            info_bbox = draw.textbbox((0, 0), info)
            info_width = info_bbox[2] - info_bbox[0]
            draw.text((center_x - info_width // 2, center_y - 20), info, fill='#4ecdc4')
            
            # Instructions
            instructions = "Open multiple browser tabs to test multi-user functionality"
            inst_bbox = draw.textbbox((0, 0), instructions)
            inst_width = inst_bbox[2] - inst_bbox[0]
            draw.text((center_x - inst_width // 2, center_y + 20), instructions, fill='#ffd93d')
            
            # Monitor info
            monitor_info = f"Monitor: {self.selected_monitor + 1} of {len(self.monitors) if self.monitors else 1}"
            mon_bbox = draw.textbbox((0, 0), monitor_info)
            mon_width = mon_bbox[2] - mon_bbox[0]
            draw.text((center_x - mon_width // 2, center_y + 60), monitor_info, fill='#ff6b6b')
            
            # Encode to base64
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.quality)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        except ImportError:
            # Ultimate fallback
            return base64.b64encode(b"Test frame - PIL not available").decode('utf-8')
    
    def _update_fps(self):
        """Update FPS counter"""
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            elapsed = current_time - self.last_fps_time
            self.actual_fps = self.frame_count / (current_time - self.start_time) if current_time > self.start_time else 0
            self.last_fps_time = current_time
            
    def get_current_frame(self):
        """Get current frame as base64 JPEG"""
        return self.current_frame
        
    def get_stats(self):
        """Get capture statistics"""
        return {
            'fps': round(self.actual_fps, 1),
            'frame_count': self.frame_count,
            'resolution': self.target_resolution,
            'quality': self.quality,
            'monitor': self.selected_monitor,
            'uptime': time.time() - self.start_time
        }
        
    def update_settings(self, fps=None, resolution=None, quality=None, monitor=None):
        """Update capture settings"""
        if fps and fps != self.target_fps:
            self.target_fps = fps
            logger.info(f"FPS updated to {fps}")
            
        if resolution and resolution != self.target_resolution:
            self.target_resolution = tuple(resolution)
            logger.info(f"Resolution updated to {self.target_resolution}")
            
        if quality and quality != self.quality:
            self.quality = quality
            logger.info(f"Quality updated to {quality}")
            
        if monitor is not None and self.select_monitor(monitor):
            logger.info(f"Monitor switched to {monitor}")

class User:
    """Represents a connected user"""
    
    def __init__(self, user_id: str, websocket: web.WebSocketResponse, name: str = None):
        self.id = user_id
        self.websocket = websocket
        self.name = name or f"User {user_id[:8]}"
        self.connected_at = time.time()
        self.is_presenter = False
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'connected_at': self.connected_at,
            'is_presenter': self.is_presenter
        }

class ScreenShareServer:
    """Main server class handling multiple users like Google Meet"""
    
    def __init__(self, host="0.0.0.0", port=8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.screen_capture = ScreenCapture()
        self.users: Dict[str, User] = {}
        self.presenter_id: Optional[str] = None
        self.room_id = str(uuid.uuid4())[:8]
        
        self._setup_cors()
        self._setup_routes()
        
    def _setup_cors(self):
        """Setup CORS for cross-origin requests"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
            
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get("/", self.serve_index)
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_get("/stream", self.serve_stream)
        self.app.router.add_get("/stats", self.serve_stats)
        self.app.router.add_post("/settings", self.handle_settings)
        self.app.router.add_get("/monitors", self.serve_monitors)
        self.app.router.add_post("/select-monitor", self.handle_monitor_selection)
        
    async def serve_index(self, request):
        """Serve the main interface"""
        html_content = self._get_html_content()
        return web.Response(text=html_content, content_type="text/html")
        
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        user_id = str(uuid.uuid4())
        user = User(user_id, ws)
        self.users[user_id] = user
        
        # If this is the first user, make them the presenter
        if not self.presenter_id:
            self.presenter_id = user_id
            user.is_presenter = True
            
        logger.info(f"User {user.name} connected. Total users: {len(self.users)}")
        
        # Send welcome message
        await self._send_to_user(user_id, {
            'type': 'welcome',
            'user_id': user_id,
            'room_id': self.room_id,
            'is_presenter': user.is_presenter,
            'users': [u.to_dict() for u in self.users.values()]
        })
        
        # Notify other users
        await self._broadcast_except(user_id, {
            'type': 'user_joined',
            'user': user.to_dict(),
            'total_users': len(self.users)
        })
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(user_id, data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            await self._user_disconnected(user_id)
            
        return ws
        
    async def _handle_message(self, user_id: str, data: dict):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'start_presenting':
            await self._start_presenting(user_id)
        elif message_type == 'stop_presenting':
            await self._stop_presenting(user_id)
        elif message_type == 'request_presenter':
            await self._request_presenter(user_id)
        elif message_type == 'chat_message':
            await self._handle_chat(user_id, data.get('message', ''))
        elif message_type == 'settings_update':
            await self._handle_settings_update(user_id, data.get('settings', {}))
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    async def _start_presenting(self, user_id: str):
        """Start screen sharing for a user"""
        if user_id not in self.users:
            return
            
        # Only the presenter can start sharing
        if self.presenter_id != user_id:
            await self._send_to_user(user_id, {
                'type': 'error',
                'message': 'Only the presenter can share screen'
            })
            return
            
        self.screen_capture.start_capture()
        
        await self._broadcast({
            'type': 'presentation_started',
            'presenter': self.users[user_id].to_dict()
        })
        
    async def _stop_presenting(self, user_id: str):
        """Stop screen sharing"""
        if user_id == self.presenter_id:
            await self.screen_capture.stop_capture()
            
            await self._broadcast({
                'type': 'presentation_stopped',
                'presenter': self.users[user_id].to_dict()
            })
            
    async def _request_presenter(self, user_id: str):
        """Request to become presenter"""
        if user_id not in self.users:
            return
            
        # For demo purposes, automatically grant presenter rights
        # In a real app, you'd ask the current presenter for permission
        if self.presenter_id:
            old_presenter = self.users.get(self.presenter_id)
            if old_presenter:
                old_presenter.is_presenter = False
                
        self.presenter_id = user_id
        self.users[user_id].is_presenter = True
        
        await self._broadcast({
            'type': 'presenter_changed',
            'new_presenter': self.users[user_id].to_dict(),
            'users': [u.to_dict() for u in self.users.values()]
        })
        
    async def _handle_chat(self, user_id: str, message: str):
        """Handle chat messages"""
        if user_id not in self.users or not message.strip():
            return
            
        chat_message = {
            'type': 'chat_message',
            'user': self.users[user_id].to_dict(),
            'message': message.strip(),
            'timestamp': time.time()
        }
        
        await self._broadcast(chat_message)
        
    async def _handle_settings_update(self, user_id: str, settings: dict):
        """Handle settings updates from presenter"""
        if user_id != self.presenter_id:
            return
            
        self.screen_capture.update_settings(
            fps=settings.get('fps'),
            resolution=settings.get('resolution'),
            quality=settings.get('quality'),
            monitor=settings.get('monitor')
        )
        
        await self._broadcast({
            'type': 'settings_updated',
            'settings': settings
        })
        
    async def _user_disconnected(self, user_id: str):
        """Handle user disconnection"""
        if user_id not in self.users:
            return
            
        user = self.users[user_id]
        del self.users[user_id]
        
        # If presenter left, stop sharing and assign new presenter
        if user_id == self.presenter_id:
            await self.screen_capture.stop_capture()
            self.presenter_id = None
            
            # Assign new presenter if users remain
            if self.users:
                new_presenter_id = next(iter(self.users))
                self.presenter_id = new_presenter_id
                self.users[new_presenter_id].is_presenter = True
                
        logger.info(f"User {user.name} disconnected. Total users: {len(self.users)}")
        
        await self._broadcast({
            'type': 'user_left',
            'user': user.to_dict(),
            'total_users': len(self.users),
            'new_presenter': self.users[self.presenter_id].to_dict() if self.presenter_id else None
        })
        
    async def _send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.users:
            try:
                await self.users[user_id].websocket.send_str(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                
    async def _broadcast(self, message: dict):
        """Broadcast message to all users"""
        if not self.users:
            return
            
        message_str = json.dumps(message)
        for user_id in list(self.users.keys()):
            try:
                await self.users[user_id].websocket.send_str(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                
    async def _broadcast_except(self, except_user_id: str, message: dict):
        """Broadcast to all users except one"""
        message_str = json.dumps(message)
        for user_id, user in self.users.items():
            if user_id != except_user_id:
                try:
                    await user.websocket.send_str(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    
    async def serve_stream(self, request):
        """Serve current frame"""
        frame = self.screen_capture.get_current_frame()
        response = {
            'frame': frame,
            'timestamp': time.time(),
            'stats': self.screen_capture.get_stats()
        }
        
        return web.json_response(response, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        
    async def serve_stats(self, request):
        """Serve statistics"""
        stats = {
            **self.screen_capture.get_stats(),
            'users': len(self.users),
            'presenter': self.users[self.presenter_id].to_dict() if self.presenter_id else None,
            'room_id': self.room_id
        }
        
        return web.json_response(stats, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        
    async def serve_monitors(self, request):
        """Serve available monitors"""
        monitors = self.screen_capture.get_monitors()
        return web.json_response({'monitors': monitors}, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        
    async def handle_settings(self, request):
        """Handle settings updates"""
        try:
            data = await request.json()
            self.screen_capture.update_settings(
                fps=data.get('fps'),
                resolution=data.get('resolution'),
                quality=data.get('quality'),
                monitor=data.get('monitor')
            )
            
            return web.json_response({'status': 'success'}, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
            
    async def handle_monitor_selection(self, request):
        """Handle monitor selection"""
        try:
            data = await request.json()
            monitor_id = data.get('monitor_id', 0)
            
            if self.screen_capture.select_monitor(monitor_id):
                return web.json_response({'status': 'success'}, headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                })
            else:
                return web.json_response({'error': 'Invalid monitor ID'}, status=400, headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            })
            
    def _get_html_content(self):
        """Get the HTML content for the interface"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Screen Share Pro - Multi-User</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .header-info {
            display: flex;
            gap: 2rem;
            align-items: center;
            font-size: 0.9rem;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .main-content {
            flex: 1;
            display: flex;
            gap: 1rem;
            padding: 1rem;
        }
        
        .video-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .video-container {
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 400px;
        }
        
        #streamImage {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 8px;
        }
        
        .video-overlay {
            position: absolute;
            top: 1rem;
            left: 1rem;
            background: rgba(0, 0, 0, 0.7);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            backdrop-filter: blur(10px);
        }
        
        .video-controls {
            display: flex;
            justify-content: center;
            gap: 1rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .btn-primary {
            background: #4CAF50;
            color: white;
        }
        
        .btn-primary:hover {
            background: #45a049;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .btn-danger {
            background: #f44336;
            color: white;
        }
        
        .btn-danger:hover {
            background: #da190b;
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .sidebar {
            width: 300px;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .panel {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 1rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .panel h3 {
            margin-bottom: 1rem;
            font-size: 1.1rem;
            color: #4ecdc4;
        }
        
        .users-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .user-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
        }
        
        .user-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(45deg, #4ecdc4, #44a08d);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.8rem;
        }
        
        .user-name {
            flex: 1;
            font-size: 0.9rem;
        }
        
        .presenter-badge {
            background: #ff6b6b;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }
        
        .stat-item {
            text-align: center;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
        }
        
        .stat-value {
            font-size: 1.2rem;
            font-weight: bold;
            color: #4ecdc4;
        }
        
        .stat-label {
            font-size: 0.8rem;
            opacity: 0.8;
        }
        
        .settings-group {
            margin-bottom: 1rem;
        }
        
        .settings-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: #ccc;
        }
        
        .settings-group select,
        .settings-group input {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 0.9rem;
        }
        
        .settings-group select option {
            background: #333;
            color: white;
        }
        
        .chat-container {
            height: 200px;
            display: flex;
            flex-direction: column;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            margin-bottom: 0.5rem;
        }
        
        .chat-message {
            margin-bottom: 0.5rem;
            font-size: 0.8rem;
        }
        
        .chat-user {
            font-weight: bold;
            color: #4ecdc4;
        }
        
        .chat-input {
            display: flex;
            gap: 0.5rem;
        }
        
        .chat-input input {
            flex: 1;
            padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        
        .placeholder {
            text-align: center;
            opacity: 0.7;
            padding: 2rem;
        }
        
        .placeholder-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        
        .error-message {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        @media (max-width: 768px) {
            .main-content {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
            }
            
            .header {
                padding: 1rem;
            }
            
            .header-info {
                flex-direction: column;
                gap: 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ Screen Share Pro</h1>
        <div class="header-info">
            <div class="user-info">
                <div class="status-dot"></div>
                <span id="userInfo">Connecting...</span>
            </div>
            <div id="roomInfo">Room: Loading...</div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="video-section">
            <div class="video-container">
                <img id="streamImage" style="display: none;" alt="Screen Stream">
                <div id="placeholder" class="placeholder">
                    <div class="placeholder-icon">🖥️</div>
                    <h3>Ready to Share</h3>
                    <p>Click "Start Sharing" to begin screen sharing</p>
                </div>
                <div id="videoOverlay" class="video-overlay" style="display: none;">
                    <span id="streamStats">FPS: -- | Resolution: --</span>
                </div>
            </div>
            
            <div class="video-controls">
                <button id="startBtn" class="btn btn-primary" disabled>Start Sharing</button>
                <button id="stopBtn" class="btn btn-danger" disabled>Stop Sharing</button>
                <button id="requestPresenterBtn" class="btn btn-secondary">Request Presenter</button>
                <button id="fullscreenBtn" class="btn btn-secondary">Fullscreen</button>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="panel">
                <h3>👥 Participants (<span id="userCount">0</span>)</h3>
                <div id="usersList" class="users-list"></div>
            </div>
            
            <div class="panel">
                <h3>📊 Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div id="fpsValue" class="stat-value">0</div>
                        <div class="stat-label">FPS</div>
                    </div>
                    <div class="stat-item">
                        <div id="qualityValue" class="stat-value">85</div>
                        <div class="stat-label">Quality</div>
                    </div>
                    <div class="stat-item">
                        <div id="resolutionValue" class="stat-value">1280x720</div>
                        <div class="stat-label">Resolution</div>
                    </div>
                    <div class="stat-item">
                        <div id="monitorValue" class="stat-value">1</div>
                        <div class="stat-label">Monitor</div>
                    </div>
                </div>
            </div>
            
            <div class="panel" id="settingsPanel" style="display: none;">
                <h3>⚙️ Settings</h3>
                <div class="settings-group">
                    <label>Quality</label>
                    <select id="qualitySelect">
                        <option value="95">Ultra (95%)</option>
                        <option value="85" selected>High (85%)</option>
                        <option value="70">Medium (70%)</option>
                        <option value="50">Low (50%)</option>
                    </select>
                </div>
                <div class="settings-group">
                    <label>FPS</label>
                    <select id="fpsSelect">
                        <option value="60" selected>60 FPS</option>
                        <option value="30">30 FPS</option>
                        <option value="15">15 FPS</option>
                    </select>
                </div>
                <div class="settings-group">
                    <label>Monitor</label>
                    <select id="monitorSelect">
                        <option value="0">Loading...</option>
                    </select>
                </div>
            </div>
            
            <div class="panel">
                <h3>💬 Chat</h3>
                <div class="chat-container">
                    <div id="chatMessages" class="chat-messages"></div>
                    <div class="chat-input">
                        <input type="text" id="chatInput" placeholder="Type a message..." maxlength="200">
                        <button id="sendChatBtn" class="btn btn-primary">Send</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        class ScreenShareClient {
            constructor() {
                this.ws = null;
                this.connected = false;
                this.userId = null;
                this.roomId = null;
                this.isPresenter = false;
                this.isSharing = false;
                this.users = {};
                this.streamInterval = null;
                
                this.initElements();
                this.bindEvents();
                this.connect();
                this.loadMonitors();
            }
            
            initElements() {
                // Video elements
                this.streamImage = document.getElementById('streamImage');
                this.placeholder = document.getElementById('placeholder');
                this.videoOverlay = document.getElementById('videoOverlay');
                this.streamStats = document.getElementById('streamStats');
                
                // Control buttons
                this.startBtn = document.getElementById('startBtn');
                this.stopBtn = document.getElementById('stopBtn');
                this.requestPresenterBtn = document.getElementById('requestPresenterBtn');
                this.fullscreenBtn = document.getElementById('fullscreenBtn');
                
                // Info displays
                this.userInfo = document.getElementById('userInfo');
                this.roomInfo = document.getElementById('roomInfo');
                this.userCount = document.getElementById('userCount');
                this.usersList = document.getElementById('usersList');
                
                // Stats
                this.fpsValue = document.getElementById('fpsValue');
                this.qualityValue = document.getElementById('qualityValue');
                this.resolutionValue = document.getElementById('resolutionValue');
                this.monitorValue = document.getElementById('monitorValue');
                
                // Settings
                this.settingsPanel = document.getElementById('settingsPanel');
                this.qualitySelect = document.getElementById('qualitySelect');
                this.fpsSelect = document.getElementById('fpsSelect');
                this.monitorSelect = document.getElementById('monitorSelect');
                
                // Chat
                this.chatMessages = document.getElementById('chatMessages');
                this.chatInput = document.getElementById('chatInput');
                this.sendChatBtn = document.getElementById('sendChatBtn');
            }
            
            bindEvents() {
                this.startBtn.addEventListener('click', () => this.startSharing());
                this.stopBtn.addEventListener('click', () => this.stopSharing());
                this.requestPresenterBtn.addEventListener('click', () => this.requestPresenter());
                this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
                
                // Settings
                this.qualitySelect.addEventListener('change', () => this.updateSettings());
                this.fpsSelect.addEventListener('change', () => this.updateSettings());
                this.monitorSelect.addEventListener('change', () => this.updateSettings());
                
                // Chat
                this.sendChatBtn.addEventListener('click', () => this.sendChat());
                this.chatInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') this.sendChat();
                });
                
                // Keyboard shortcuts
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'f' || e.key === 'F') {
                        e.preventDefault();
                        this.toggleFullscreen();
                    }
                });
            }
            
            connect() {
                const wsUrl = `ws://${window.location.host}/ws`;
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('Connected to server');
                    this.connected = true;
                };
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                };
                
                this.ws.onclose = () => {
                    console.log('Disconnected from server');
                    this.connected = false;
                    this.userInfo.textContent = 'Disconnected';
                    
                    // Attempt to reconnect
                    setTimeout(() => this.connect(), 3000);
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }
            
            handleMessage(data) {
                switch (data.type) {
                    case 'welcome':
                        this.userId = data.user_id;
                        this.roomId = data.room_id;
                        this.isPresenter = data.is_presenter;
                        this.users = {};
                        data.users.forEach(user => {
                            this.users[user.id] = user;
                        });
                        this.updateUI();
                        break;
                        
                    case 'user_joined':
                        this.users[data.user.id] = data.user;
                        this.updateUsersList();
                        this.userCount.textContent = data.total_users;
                        this.addChatMessage('System', `${data.user.name} joined the room`);
                        break;
                        
                    case 'user_left':
                        delete this.users[data.user.id];
                        this.updateUsersList();
                        this.userCount.textContent = data.total_users;
                        this.addChatMessage('System', `${data.user.name} left the room`);
                        
                        if (data.new_presenter) {
                            this.users[data.new_presenter.id] = data.new_presenter;
                            if (data.new_presenter.id === this.userId) {
                                this.isPresenter = true;
                                this.updateUI();
                            }
                        }
                        break;
                        
                    case 'presenter_changed':
                        this.users[data.new_presenter.id] = data.new_presenter;
                        this.isPresenter = data.new_presenter.id === this.userId;
                        data.users.forEach(user => {
                            this.users[user.id] = user;
                        });
                        this.updateUI();
                        this.addChatMessage('System', `${data.new_presenter.name} is now the presenter`);
                        break;
                        
                    case 'presentation_started':
                        this.isSharing = true;
                        this.startStreamPolling();
                        this.addChatMessage('System', `${data.presenter.name} started sharing screen`);
                        break;
                        
                    case 'presentation_stopped':
                        this.isSharing = false;
                        this.stopStreamPolling();
                        this.addChatMessage('System', `${data.presenter.name} stopped sharing screen`);
                        break;
                        
                    case 'chat_message':
                        this.addChatMessage(data.user.name, data.message);
                        break;
                        
                    case 'settings_updated':
                        this.updateStatsDisplay(data.settings);
                        break;
                        
                    case 'error':
                        this.showError(data.message);
                        break;
                }
            }
            
            updateUI() {
                this.userInfo.textContent = this.isPresenter ? 'You (Presenter)' : 'You (Viewer)';
                this.roomInfo.textContent = `Room: ${this.roomId}`;
                this.userCount.textContent = Object.keys(this.users).length;
                
                this.startBtn.disabled = !this.isPresenter;
                this.stopBtn.disabled = !this.isPresenter || !this.isSharing;
                this.requestPresenterBtn.disabled = this.isPresenter;
                
                this.settingsPanel.style.display = this.isPresenter ? 'block' : 'none';
                
                this.updateUsersList();
            }
            
            updateUsersList() {
                this.usersList.innerHTML = '';
                
                Object.values(this.users).forEach(user => {
                    const userItem = document.createElement('div');
                    userItem.className = 'user-item';
                    
                    const avatar = document.createElement('div');
                    avatar.className = 'user-avatar';
                    avatar.textContent = user.name.charAt(0).toUpperCase();
                    
                    const name = document.createElement('div');
                    name.className = 'user-name';
                    name.textContent = user.name;
                    
                    userItem.appendChild(avatar);
                    userItem.appendChild(name);
                    
                    if (user.is_presenter) {
                        const badge = document.createElement('div');
                        badge.className = 'presenter-badge';
                        badge.textContent = 'PRESENTER';
                        userItem.appendChild(badge);
                    }
                    
                    this.usersList.appendChild(userItem);
                });
            }
            
            startSharing() {
                if (!this.isPresenter) return;
                
                this.sendMessage({
                    type: 'start_presenting'
                });
            }
            
            stopSharing() {
                if (!this.isPresenter) return;
                
                this.sendMessage({
                    type: 'stop_presenting'
                });
            }
            
            requestPresenter() {
                this.sendMessage({
                    type: 'request_presenter'
                });
            }
            
            startStreamPolling() {
                if (this.streamInterval) return;
                
                this.streamInterval = setInterval(async () => {
                    try {
                        const response = await fetch('/stream');
                        const data = await response.json();
                        
                        if (data.frame) {
                            this.streamImage.src = 'data:image/jpeg;base64,' + data.frame;
                            this.streamImage.style.display = 'block';
                            this.placeholder.style.display = 'none';
                            this.videoOverlay.style.display = 'block';
                            
                            this.updateStatsDisplay(data.stats);
                        }
                    } catch (error) {
                        console.error('Stream fetch error:', error);
                    }
                }, 1000 / 30); // 30 FPS polling
            }
            
            stopStreamPolling() {
                if (this.streamInterval) {
                    clearInterval(this.streamInterval);
                    this.streamInterval = null;
                }
                
                this.streamImage.style.display = 'none';
                this.placeholder.style.display = 'block';
                this.videoOverlay.style.display = 'none';
            }
            
            updateStatsDisplay(stats) {
                if (stats.fps !== undefined) {
                    this.fpsValue.textContent = stats.fps;
                    this.streamStats.textContent = `FPS: ${stats.fps} | Resolution: ${stats.resolution[0]}x${stats.resolution[1]}`;
                }
                if (stats.quality !== undefined) {
                    this.qualityValue.textContent = stats.quality;
                }
                if (stats.resolution !== undefined) {
                    this.resolutionValue.textContent = `${stats.resolution[0]}x${stats.resolution[1]}`;
                }
                if (stats.monitor !== undefined) {
                    this.monitorValue.textContent = stats.monitor + 1;
                }
            }
            
            updateSettings() {
                if (!this.isPresenter) return;
                
                const settings = {
                    quality: parseInt(this.qualitySelect.value),
                    fps: parseInt(this.fpsSelect.value),
                    monitor: parseInt(this.monitorSelect.value)
                };
                
                this.sendMessage({
                    type: 'settings_update',
                    settings: settings
                });
                
                // Also update server directly
                fetch('/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                }).catch(console.error);
            }
            
            async loadMonitors() {
                try {
                    const response = await fetch('/monitors');
                    const data = await response.json();
                    
                    this.monitorSelect.innerHTML = '';
                    data.monitors.forEach(monitor => {
                        const option = document.createElement('option');
                        option.value = monitor.id;
                        option.textContent = `${monitor.name} (${monitor.width}x${monitor.height})${monitor.primary ? ' - Primary' : ''}`;
                        this.monitorSelect.appendChild(option);
                    });
                } catch (error) {
                    console.error('Failed to load monitors:', error);
                }
            }
            
            sendChat() {
                const message = this.chatInput.value.trim();
                if (!message) return;
                
                this.sendMessage({
                    type: 'chat_message',
                    message: message
                });
                
                this.chatInput.value = '';
            }
            
            addChatMessage(user, message) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'chat-message';
                
                const userSpan = document.createElement('span');
                userSpan.className = 'chat-user';
                userSpan.textContent = user + ': ';
                
                messageDiv.appendChild(userSpan);
                messageDiv.appendChild(document.createTextNode(message));
                
                this.chatMessages.appendChild(messageDiv);
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
            
            toggleFullscreen() {
                if (!document.fullscreenElement) {
                    this.streamImage.requestFullscreen().catch(console.error);
                } else {
                    document.exitFullscreen();
                }
            }
            
            showError(message) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = message;
                document.body.appendChild(errorDiv);
                
                setTimeout(() => errorDiv.remove(), 5000);
            }
            
            sendMessage(message) {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify(message));
                }
            }
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new ScreenShareClient();
        });
    </script>
</body>
</html>'''
        
    async def start_server(self):
        """Start the server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        return runner
        
    async def cleanup(self):
        """Cleanup resources"""
        await self.screen_capture.stop_capture()
        
        # Close all user connections
        for user in list(self.users.values()):
            try:
                await user.websocket.close()
            except:
                pass
        self.users.clear()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Unified Screen Sharing Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--fps", type=int, default=60, help="Target FPS")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality (1-100)")
    
    args = parser.parse_args()
    
    print("🖥️  Screen Share Pro - Multi-User Edition")
    print("=" * 50)
    print(f"Server: http://{args.host}:{args.port}")
    print(f"Target FPS: {args.fps}")
    print(f"Quality: {args.quality}%")
    print("=" * 50)
    print()
    print("📋 How to test with multiple users:")
    print("1. Start this server")
    print("2. Open http://localhost:8080 in multiple browser tabs/windows")
    print("3. Each tab represents a different user")
    print("4. The first user becomes the presenter automatically")
    print("5. Only the presenter can start/stop screen sharing")
    print("6. Other users can request presenter rights")
    print("7. Test chat functionality between users")
    print("8. Try different browsers (Chrome, Firefox, Safari, Edge)")
    print()
    
    # Create and start server
    server = ScreenShareServer(args.host, args.port)
    server.screen_capture.target_fps = args.fps
    server.screen_capture.quality = args.quality
    
    runner = await server.start_server()
    
    print(f"✅ Server running at http://{args.host}:{args.port}")
    print("🌐 Open the URL in multiple browser tabs to test multi-user functionality")
    print("⌨️  Press Ctrl+C to stop")
    print()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down...")
        raise KeyboardInterrupt()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Keep server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
    finally:
        await server.cleanup()
        await runner.cleanup()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(main())