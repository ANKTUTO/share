import time
import numpy as np
import cv2
from mss import mss
import asyncio
from threading import Thread
import queue
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ScreenCapture:
    """High-performance screen capture with 60 FPS capability"""
    
    def __init__(self, target_fps: int = 60, target_resolution: Tuple[int, int] = (1280, 720)):
        self.target_fps = target_fps
        self.target_resolution = target_resolution
        self.frame_interval = 1.0 / target_fps
        self.sct = mss()
        self.running = False
        self.frame_queue = queue.Queue(maxsize=5)  # Small buffer to prevent memory issues
        self.current_frame = None
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.actual_fps = 0
        
        # Get primary monitor
        self.monitor = self.sct.monitors[1]  # Index 0 is all monitors combined
        logger.info(f"Primary monitor: {self.monitor}")
        
    def start_capture(self):
        """Start the screen capture in a separate thread"""
        if self.running:
            return
            
        self.running = True
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info(f"Screen capture started at {self.target_fps} FPS, target resolution: {self.target_resolution}")
        
    def stop_capture(self):
        """Stop the screen capture"""
        self.running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        logger.info("Screen capture stopped")
        
    def _capture_loop(self):
        """Main capture loop running at target FPS"""
        next_frame_time = time.time()
        
        while self.running:
            frame_start = time.time()
            
            try:
                # Capture screen
                screenshot = self.sct.grab(self.monitor)
                
                # Convert to numpy array
                frame = np.array(screenshot)
                
                # Convert BGRA to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                
                # Resize to target resolution for performance
                if frame.shape[:2] != self.target_resolution[::-1]:  # height, width
                    frame = cv2.resize(frame, self.target_resolution, interpolation=cv2.INTER_LINEAR)
                
                # Update current frame
                self.current_frame = frame
                
                # Update FPS calculation
                self._update_fps()
                
                # Try to add to queue without blocking
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Remove oldest frame if queue is full
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
                        
            except Exception as e:
                logger.error(f"Error capturing screen: {e}")
                continue
                
            # Maintain target FPS
            next_frame_time += self.frame_interval
            sleep_time = next_frame_time - time.time()
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # We're behind schedule, adjust next frame time
                next_frame_time = time.time()
                
    def _update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_fps_time >= 1.0:
            self.actual_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame"""
        return self.current_frame
        
    def get_frame_from_queue(self) -> Optional[np.ndarray]:
        """Get frame from queue (non-blocking)"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
            
    def get_fps(self) -> float:
        """Get actual FPS"""
        return self.actual_fps
        
    def get_resolution(self) -> Tuple[int, int]:
        """Get current resolution"""
        return self.target_resolution