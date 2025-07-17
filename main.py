#!/usr/bin/env python3
"""
High-Performance Screen Sharing Software
Main entry point with CLI interface
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from screen_capture import ScreenCapture
from webrtc_server import WebRTCServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScreenShareApp:
    """Main application class"""
    
    def __init__(self, args):
        self.args = args
        self.screen_capture = None
        self.webrtc_server = None
        self.running = False
        
    async def start(self):
        """Start the screen sharing application"""
        logger.info("Starting High-Performance Screen Sharing Software")
        logger.info(f"Target FPS: {self.args.fps}")
        logger.info(f"Target Resolution: {self.args.width}x{self.args.height}")
        logger.info(f"Server: {self.args.host}:{self.args.port}")
        
        try:
            # Initialize screen capture
            self.screen_capture = ScreenCapture(
                target_fps=self.args.fps,
                target_resolution=(self.args.width, self.args.height)
            )
            
            # Initialize WebRTC server
            self.webrtc_server = WebRTCServer(
                screen_capture=self.screen_capture,
                host=self.args.host,
                port=self.args.port
            )
            
            # Start screen capture
            self.screen_capture.start_capture()
            
            # Start web server
            runner = await self.webrtc_server.start_server()
            
            self.running = True
            logger.info("✅ Screen sharing server is running!")
            logger.info(f"🌐 Open http://{self.args.host}:{self.args.port} to view the stream")
            logger.info("Press Ctrl+C to stop")
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
                
                # Log performance stats periodically
                if hasattr(self, '_last_stats_time'):
                    import time
                    if time.time() - self._last_stats_time > 10:  # Every 10 seconds
                        await self._log_stats()
                        self._last_stats_time = time.time()
                else:
                    import time
                    self._last_stats_time = time.time()
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        if self.screen_capture:
            self.screen_capture.stop_capture()
            
        if self.webrtc_server:
            await self.webrtc_server.cleanup()
            
        logger.info("Cleanup complete")
        
    async def _log_stats(self):
        """Log performance statistics"""
        if self.screen_capture:
            actual_fps = self.screen_capture.get_fps()
            logger.info(f"📊 Performance: {actual_fps:.1f} FPS")
            
    def stop(self):
        """Stop the application"""
        self.running = False

def create_directories():
    """Create necessary directories"""
    web_dir = Path("web")
    web_dir.mkdir(exist_ok=True)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="High-Performance Screen Sharing Software",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host address"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port"
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Target frames per second"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Target width resolution"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Target height resolution"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create directories
    create_directories()
    
    # Create application
    app = ScreenShareApp(args)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        app.stop()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run application
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("Application interrupted")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)
    
    logger.info("Application stopped")

if __name__ == "__main__":
    main()