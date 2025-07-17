import asyncio
import json
import logging
import time
from aiohttp import web, WSMsgType
from aiohttp_cors import setup as cors_setup, CorsConfig
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer, MediaRelay
import av
import numpy as np
from screen_capture import ScreenCapture
from typing import Set, Optional

logger = logging.getLogger(__name__)

class ScreenStreamTrack(VideoStreamTrack):
    """Custom video track for screen sharing"""
    
    def __init__(self, screen_capture: ScreenCapture):
        super().__init__()
        self.screen_capture = screen_capture
        self.pts = 0
        self.time_base = av.time_base.Fraction(1, 1000000)  # Microseconds
        
    async def recv(self):
        """Receive the next frame"""
        # Get frame from screen capture
        frame = self.screen_capture.get_latest_frame()
        if frame is None:
            # Return black frame if no frame available
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            
        # Create AV frame
        av_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        
        # Set timestamp
        av_frame.pts = self.pts
        av_frame.time_base = self.time_base
        
        # Increment pts for next frame (60 FPS = 16666 microseconds per frame)
        self.pts += 16666
        
        return av_frame

class WebRTCServer:
    """WebRTC signaling server and peer connection manager"""
    
    def __init__(self, screen_capture: ScreenCapture, host: str = "0.0.0.0", port: int = 8080):
        self.screen_capture = screen_capture
        self.host = host
        self.port = port
        self.app = web.Application()
        self.connections: Set[RTCPeerConnection] = set()
        self.websockets: Set[web.WebSocketResponse] = set()
        
        # Setup CORS
        cors = cors_setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Setup routes
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/ws", self.websocket_handler)
        self.app.router.add_static("/static", "web", show_index=True)
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
            
        # ICE servers for better connectivity
        self.ice_servers = [
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
        ]
        
    async def index(self, request):
        """Serve the main viewer page"""
        with open("web/index.html", "r") as f:
            content = f.read()
        return web.Response(text=content, content_type="text/html")
        
    async def websocket_handler(self, request):
        """Handle WebSocket connections for signaling"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info(f"New WebSocket connection. Total connections: {len(self.websockets)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_message(ws, data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket connection closed. Total connections: {len(self.websockets)}")
            
        return ws
        
    async def handle_message(self, ws, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "offer":
            await self.handle_offer(ws, data)
        elif message_type == "ice-candidate":
            await self.handle_ice_candidate(ws, data)
        elif message_type == "stats-request":
            await self.send_stats(ws)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            
    async def handle_offer(self, ws, data):
        """Handle WebRTC offer"""
        try:
            # Create peer connection
            config = RTCConfiguration(iceServers=self.ice_servers)
            pc = RTCPeerConnection(configuration=config)
            self.connections.add(pc)
            
            # Add screen stream track
            screen_track = ScreenStreamTrack(self.screen_capture)
            pc.addTrack(screen_track)
            
            # Handle connection state changes
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state: {pc.connectionState}")
                if pc.connectionState == "closed":
                    self.connections.discard(pc)
                    
            # Handle ICE candidates
            @pc.on("icecandidate")
            async def on_icecandidate(candidate):
                if candidate:
                    await self.send_message(ws, {
                        "type": "ice-candidate",
                        "candidate": {
                            "candidate": candidate.candidate,
                            "sdpMLineIndex": candidate.sdpMLineIndex,
                            "sdpMid": candidate.sdpMid
                        }
                    })
                    
            # Set remote description
            offer = RTCSessionDescription(
                sdp=data["sdp"],
                type=data["type"]
            )
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            # Send answer
            await self.send_message(ws, {
                "type": "answer",
                "sdp": pc.localDescription.sdp
            })
            
        except Exception as e:
            logger.error(f"Error handling offer: {e}")
            await self.send_message(ws, {
                "type": "error",
                "message": str(e)
            })
            
    async def handle_ice_candidate(self, ws, data):
        """Handle ICE candidate"""
        # Note: This is a simplified implementation
        # In a real scenario, you'd need to associate candidates with specific peer connections
        logger.info("ICE candidate received")
        
    async def send_stats(self, ws):
        """Send performance statistics"""
        stats = {
            "type": "stats",
            "fps": self.screen_capture.get_fps(),
            "resolution": self.screen_capture.get_resolution(),
            "connections": len(self.connections),
            "timestamp": time.time()
        }
        await self.send_message(ws, stats)
        
    async def send_message(self, ws, message):
        """Send message to WebSocket"""
        try:
            await ws.send_str(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    async def broadcast_message(self, message):
        """Broadcast message to all connected WebSockets"""
        if not self.websockets:
            return
            
        message_str = json.dumps(message)
        for ws in self.websockets.copy():
            try:
                await ws.send_str(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                self.websockets.discard(ws)
                
    async def cleanup(self):
        """Clean up connections"""
        for pc in self.connections.copy():
            await pc.close()
        self.connections.clear()
        
        for ws in self.websockets.copy():
            await ws.close()
        self.websockets.clear()
        
    async def start_server(self):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"WebRTC server started at http://{self.host}:{self.port}")
        return runner