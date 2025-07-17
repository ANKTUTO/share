#!/usr/bin/env python3
"""
Simplified Screen Sharing Server
WebContainer-compatible version using only available Python modules
"""

import http.server
import socketserver
import json
import threading
import time
import base64
from urllib.parse import urlparse, parse_qs
import os
import sys

# Check if we can import required modules
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("Warning: mss not available, using placeholder")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: opencv-python not available, using placeholder")

class ScreenCaptureSimple:
    """Simplified screen capture for WebContainer environment"""
    
    def __init__(self, target_fps=60, target_resolution=(1280, 720), bitrate=5000):
        self.target_fps = target_fps
        self.target_resolution = target_resolution
        self.bitrate = bitrate
        self.running = False
        self.current_frame = None
        self.frame_count = 0
        self.start_time = time.time()
        self.quality_mode = 'high'  # high, medium, low, ultra
        
    def start_capture(self):
        """Start screen capture in a separate thread"""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        print(f"Screen capture started at {self.target_fps} FPS")
        
    def update_settings(self, fps=None, resolution=None, bitrate=None, quality=None):
        """Update capture settings dynamically"""
        if fps:
            self.target_fps = fps
        if resolution:
            self.target_resolution = resolution
        if bitrate:
            self.bitrate = bitrate
        if quality:
            self.quality_mode = quality
        print(f"Settings updated: {self.target_fps}FPS, {self.target_resolution}, {self.bitrate}kbps")
        
    def stop_capture(self):
        """Stop screen capture"""
        self.running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1)
        print("Screen capture stopped")
        
    def _capture_loop(self):
        """Main capture loop"""
        frame_interval = 1.0 / self.target_fps
        
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                
                while self.running:
                    start_time = time.time()
                    
                    # Capture screen
                    screenshot = sct.grab(monitor)
                    
                    if CV2_AVAILABLE:
                        # Convert to numpy array and resize
                        import numpy as np
                        frame = np.array(screenshot)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                        frame = cv2.resize(frame, self.target_resolution)
                        
                        # Encode to JPEG with quality based on bitrate
                        quality = min(95, max(50, int(self.bitrate / 100)))
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                        self.current_frame = base64.b64encode(buffer).decode('utf-8')
                    else:
                        # Fallback: use PIL if available
                        try:
                            from PIL import Image
                            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                            img = img.resize(self.target_resolution, Image.Resampling.LANCZOS)
                            
                            # Adjust quality based on bitrate
                            quality = min(95, max(50, int(self.bitrate / 100)))
                            import io
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=quality)
                            self.current_frame = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        except ImportError:
                            # Ultimate fallback: generate test pattern
                            self.current_frame = self._generate_test_frame()
                    
                    self.frame_count += 1
                    
                    # Maintain target FPS
                    elapsed = time.time() - start_time
                    sleep_time = max(0, frame_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
        else:
            # Fallback when mss is not available
            while self.running:
                start_time = time.time()
                self.current_frame = self._generate_test_frame()
                self.frame_count += 1
                
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def _generate_test_frame(self):
        """Generate a test pattern frame"""
        # Create a simple test pattern
        width, height = self.target_resolution
        
        # Generate a simple gradient pattern
        import io
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(img)
            
            # Draw some test patterns
            for i in range(0, width, 50):
                color = (i % 255, (i * 2) % 255, (i * 3) % 255)
                draw.rectangle([i, 0, i + 25, height], fill=color)
            
            # Add timestamp
            timestamp = f"Frame: {self.frame_count} | Time: {time.time():.1f}"
            draw.text((10, 10), timestamp, fill='white')
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=80)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except ImportError:
            # Most basic fallback
            return base64.b64encode(b"Test frame data").decode('utf-8')
    
    def get_current_frame(self):
        """Get the current frame as base64 encoded JPEG"""
        return self.current_frame
    
    def get_fps(self):
        """Get actual FPS"""
        if self.frame_count == 0:
            return 0
        elapsed = time.time() - self.start_time
        return self.frame_count / elapsed if elapsed > 0 else 0

class StreamingHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for streaming server"""
    
    def __init__(self, *args, screen_capture=None, **kwargs):
        self.screen_capture = screen_capture
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_index()
        elif parsed_path.path == '/stream':
            self.serve_stream()
        elif parsed_path.path == '/stats':
            self.serve_stats()
        elif parsed_path.path == '/settings' and self.command == 'POST':
            self.handle_settings_update()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/settings':
            self.handle_settings_update()
        else:
            self.send_error(404)
    
    def handle_settings_update(self):
        """Handle settings updates"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            settings = json.loads(post_data.decode('utf-8'))
            
            if self.screen_capture:
                self.screen_capture.update_settings(
                    fps=settings.get('fps'),
                    resolution=tuple(settings.get('resolution', [])) if settings.get('resolution') else None,
                    bitrate=settings.get('bitrate'),
                    quality=settings.get('quality')
                )
            
            response = json.dumps({'status': 'success'})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(response.encode()))
            self.end_headers()
            self.wfile.write(response.encode())
            
        except Exception as e:
            error_response = json.dumps({'error': str(e)})
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(error_response.encode()))
            self.end_headers()
            self.wfile.write(error_response.encode())
    
    def serve_index(self):
        """Serve the main HTML page"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>High-Performance Screen Share</title>
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
            display: flex;
            flex-direction: column;
            color: white;
        }
        
        .header {
            padding: 20px;
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            gap: 20px;
        }
        
        .video-container {
            position: relative;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        #streamImage {
            display: block;
            max-width: 90vw;
            max-height: 70vh;
            width: auto;
            height: auto;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            align-items: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 15px 25px;
            border-radius: 50px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        
        .btn.active {
            background: #4CAF50;
        }
        
        .stats {
            display: flex;
            gap: 20px;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .stat-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            opacity: 0.7;
        }
        
        .error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ High-Performance Screen Share</h1>
        <p>Real-time screen streaming at 60 FPS</p>
    </div>
    
    <div class="main-content">
        <div class="video-container">
            <img id="streamImage" alt="Screen Stream" style="display: none;">
            <div id="loading" class="loading">
                <h3>🔄 Initializing stream...</h3>
                <p>Connecting to screen capture</p>
            </div>
        </div>
        
        <div class="controls">
            <button id="toggleBtn" class="btn">▶️ Start Stream</button>
            <button id="fullscreenBtn" class="btn">🔍 Fullscreen</button>
            <select id="qualitySelect" class="btn">
                <option value="ultra">Ultra HD (60fps)</option>
                <option value="high" selected>High (60fps)</option>
                <option value="medium">Medium (30fps)</option>
                <option value="low">Low (30fps)</option>
            </select>
            <div class="stats">
                <div class="stat-item">
                    <div class="status-indicator"></div>
                    <span id="fpsDisplay">FPS: --</span>
                </div>
                <div class="stat-item">
                    <span id="statusDisplay">Status: Disconnected</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        class ScreenStreamViewer {
            constructor() {
                this.streaming = false;
                this.streamInterval = null;
                this.frameCount = 0;
                this.lastFrameTime = Date.now();
                
                this.initElements();
                this.bindEvents();
                this.updateStats();
            }
            
            initElements() {
                this.streamImage = document.getElementById('streamImage');
                this.loading = document.getElementById('loading');
                this.toggleBtn = document.getElementById('toggleBtn');
                this.fullscreenBtn = document.getElementById('fullscreenBtn');
                this.fpsDisplay = document.getElementById('fpsDisplay');
                this.statusDisplay = document.getElementById('statusDisplay');
                this.qualitySelect = document.getElementById('qualitySelect');
            }
            
            bindEvents() {
                this.toggleBtn.addEventListener('click', () => this.toggleStream());
                this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
                this.qualitySelect.addEventListener('change', (e) => this.updateQuality(e.target.value));
                
                // Keyboard shortcuts
                document.addEventListener('keydown', (e) => {
                    if (e.code === 'Space') {
                        e.preventDefault();
                        this.toggleStream();
                    } else if (e.code === 'KeyF') {
                        e.preventDefault();
                        this.toggleFullscreen();
                    }
                });
            }
            
            async toggleStream() {
                if (this.streaming) {
                    this.stopStream();
                } else {
                    await this.startStream();
                }
            }
            
            async startStream() {
                try {
                    this.streaming = true;
                    this.toggleBtn.textContent = '⏸️ Stop Stream';
                    this.toggleBtn.classList.add('active');
                    this.statusDisplay.textContent = 'Status: Connecting...';
                    
                    // Start streaming loop
                    this.streamInterval = setInterval(() => this.fetchFrame(), 1000 / 30); // 30 FPS polling
                    
                    this.statusDisplay.textContent = 'Status: Connected';
                } catch (error) {
                    console.error('Failed to start stream:', error);
                    this.showError('Failed to start stream: ' + error.message);
                    this.stopStream();
                }
            }
            
            stopStream() {
                this.streaming = false;
                this.toggleBtn.textContent = '▶️ Start Stream';
                this.toggleBtn.classList.remove('active');
                this.statusDisplay.textContent = 'Status: Disconnected';
                
                if (this.streamInterval) {
                    clearInterval(this.streamInterval);
                    this.streamInterval = null;
                }
                
                this.streamImage.style.display = 'none';
                this.loading.style.display = 'block';
                this.loading.innerHTML = '<h3>⏹️ Stream stopped</h3><p>Click Start Stream to reconnect</p>';
            }
            
            async updateQuality(quality) {
                const qualitySettings = {
                    ultra: { fps: 60, resolution: [1920, 1080], bitrate: 8000 },
                    high: { fps: 60, resolution: [1280, 720], bitrate: 5000 },
                    medium: { fps: 30, resolution: [1280, 720], bitrate: 3000 },
                    low: { fps: 30, resolution: [854, 480], bitrate: 1500 }
                };
                
                const settings = qualitySettings[quality];
                if (settings) {
                    try {
                        await fetch('/settings', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(settings)
                        });
                        console.log('Quality updated to:', quality);
                    } catch (error) {
                        console.error('Failed to update quality:', error);
                    }
                }
            }
            
            async fetchFrame() {
                if (!this.streaming) return;
                
                try {
                    const response = await fetch('/stream');
                    if (!response.ok) throw new Error('Stream unavailable');
                    
                    const data = await response.json();
                    if (data.frame) {
                        this.streamImage.src = 'data:image/jpeg;base64,' + data.frame;
                        this.streamImage.style.display = 'block';
                        this.loading.style.display = 'none';
                        
                        this.frameCount++;
                        this.updateFPS();
                    }
                } catch (error) {
                    console.error('Frame fetch error:', error);
                    if (this.streaming) {
                        this.showError('Connection lost: ' + error.message);
                    }
                }
            }
            
            updateFPS() {
                const now = Date.now();
                const elapsed = (now - this.lastFrameTime) / 1000;
                
                if (elapsed >= 1) {
                    const fps = this.frameCount / elapsed;
                    this.fpsDisplay.textContent = `FPS: ${fps.toFixed(1)}`;
                    this.frameCount = 0;
                    this.lastFrameTime = now;
                }
            }
            
            updateStats() {
                // Update stats periodically
                setInterval(async () => {
                    if (!this.streaming) return;
                    
                    try {
                        const response = await fetch('/stats');
                        const stats = await response.json();
                        // Could display additional stats here
                    } catch (error) {
                        // Ignore stats errors
                    }
                }, 5000);
            }
            
            toggleFullscreen() {
                if (!document.fullscreenElement) {
                    this.streamImage.requestFullscreen().catch(err => {
                        console.error('Fullscreen error:', err);
                    });
                } else {
                    document.exitFullscreen();
                }
            }
            
            showError(message) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error';
                errorDiv.textContent = message;
                document.body.appendChild(errorDiv);
                
                setTimeout(() => errorDiv.remove(), 5000);
            }
        }
        
        // Initialize viewer when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new ScreenStreamViewer();
        });
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', len(html_content.encode()))
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_stream(self):
        """Serve current frame"""
        if self.screen_capture:
            frame = self.screen_capture.get_current_frame()
            response = json.dumps({'frame': frame, 'timestamp': time.time()})
        else:
            response = json.dumps({'error': 'Screen capture not available'})
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(response.encode()))
        self.end_headers()
        self.wfile.write(response.encode())
    
    def serve_stats(self):
        """Serve performance stats"""
        if self.screen_capture:
            stats = {
                'fps': self.screen_capture.get_fps(),
                'frame_count': self.screen_capture.frame_count,
                'uptime': time.time() - self.screen_capture.start_time
            }
        else:
            stats = {'error': 'Screen capture not available'}
        
        response = json.dumps(stats)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(response.encode()))
        self.end_headers()
        self.wfile.write(response.encode())

def create_handler(screen_capture):
    """Create handler with screen capture instance"""
    def handler(*args, **kwargs):
        return StreamingHandler(*args, screen_capture=screen_capture, **kwargs)
    return handler

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Screen Sharing Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--fps", type=int, default=60, help="Target FPS")
    parser.add_argument("--bitrate", type=int, default=5000, help="Target bitrate (kbps)")
    parser.add_argument("--quality", choices=['ultra', 'high', 'medium', 'low'], default='high', help="Quality preset")
    
    args = parser.parse_args()
    
    print("🖥️  High-Performance Screen Sharing Software")
    print("=" * 50)
    print(f"Target FPS: {args.fps}")
    print(f"Server: http://{args.host}:{args.port}")
    print("=" * 50)
    
    # Initialize screen capture
    screen_capture = ScreenCaptureSimple(target_fps=args.fps, bitrate=args.bitrate)
    screen_capture.start_capture()
    
    # Create HTTP server
    handler = create_handler(screen_capture)
    
    try:
        with socketserver.TCPServer((args.host, args.port), handler) as httpd:
            print(f"✅ Server running at http://{args.host}:{args.port}")
            print("🌐 Open the URL in your browser to view the stream")
            print("⌨️  Press Ctrl+C to stop")
            print()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        screen_capture.stop_capture()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    main()