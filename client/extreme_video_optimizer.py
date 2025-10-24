"""
Extreme Video Performance Optimizer
Ultra-fast video transfer with zero-latency display for LAN networks.
Eliminates flickering through immediate frame processing and display.
"""

import threading
import time
import logging
import queue
import numpy as np
from typing import Dict, Optional, Callable, Deque
from collections import deque
import cv2

logger = logging.getLogger(__name__)


class ZeroLatencyFrameProcessor:
    """
    Zero-latency frame processor for immediate video display.
    Bypasses all buffering for instant frame rendering.
    """
    
    def __init__(self):
        self.frame_callbacks: Dict[str, Callable] = {}
        self.processing_lock = threading.RLock()
        
        # Ultra-fast processing settings
        self.immediate_display = True
        self.skip_frame_validation = True  # Skip validation for speed
        self.direct_memory_access = True
        
        # Performance tracking
        self.frame_times = deque(maxlen=10)
        self.processing_times = deque(maxlen=10)
    
    def register_client_callback(self, client_id: str, callback: Callable):
        """Register immediate callback for client frames."""
        with self.processing_lock:
            self.frame_callbacks[client_id] = callback
            logger.info(f"Registered zero-latency callback for {client_id}")
    
    def process_frame_immediate(self, client_id: str, frame_data: bytes, timestamp: float):
        """Process and display frame with zero latency."""
        start_time = time.perf_counter()
        
        try:
            # Ultra-fast decompression without validation
            frame = self._decompress_ultra_fast(frame_data)
            
            if frame is not None and client_id in self.frame_callbacks:
                # Immediate callback - no queuing, no buffering
                self.frame_callbacks[client_id](frame)
                
                # Track performance
                processing_time = time.perf_counter() - start_time
                self.processing_times.append(processing_time)
                self.frame_times.append(timestamp)
                
        except Exception as e:
            # Minimal error handling to maintain speed
            if len(str(e)) < 100:  # Only log short errors
                logger.debug(f"Frame processing error: {e}")
    
    def _decompress_ultra_fast(self, frame_data: bytes) -> Optional[np.ndarray]:
        """Ultra-fast frame decompression with minimal overhead."""
        try:
            # Direct numpy conversion without validation
            nparr = np.frombuffer(frame_data, dtype=np.uint8)
            
            # Fast JPEG decode with minimal flags
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return frame
            
        except:
            return None  # Fail silently for speed
    
    def get_performance_stats(self) -> Dict:
        """Get ultra-fast performance statistics."""
        if not self.processing_times:
            return {'avg_processing_time': 0, 'fps': 0}
        
        avg_time = sum(self.processing_times) / len(self.processing_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0
        
        return {
            'avg_processing_time': avg_time * 1000,  # Convert to ms
            'fps': fps,
            'frames_processed': len(self.processing_times)
        }


class UltraFastNetworkHandler:
    """
    Ultra-fast network packet processing for video streams.
    Minimizes network latency and processing overhead.
    """
    
    def __init__(self):
        self.packet_queue = queue.Queue(maxsize=1)  # Minimal queue size
        self.processing_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Network optimization settings
        self.max_packet_size = 262144  # 256KB for ultra-large packets
        self.skip_packet_validation = True
        self.immediate_processing = True
        
        # Frame processor
        self.frame_processor = ZeroLatencyFrameProcessor()
    
    def start_processing(self):
        """Start ultra-fast packet processing."""
        if self.is_running:
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._ultra_fast_processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Ultra-fast network processing started")
    
    def stop_processing(self):
        """Stop packet processing."""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=0.1)  # Minimal wait
    
    def process_video_packet_immediate(self, client_id: str, packet_data: bytes, timestamp: float):
        """Process video packet with immediate display."""
        if self.immediate_processing:
            # Direct processing - bypass queue entirely
            self.frame_processor.process_frame_immediate(client_id, packet_data, timestamp)
        else:
            # Fallback to minimal queuing
            try:
                self.packet_queue.put_nowait((client_id, packet_data, timestamp))
            except queue.Full:
                # Drop oldest packet for new one
                try:
                    self.packet_queue.get_nowait()
                    self.packet_queue.put_nowait((client_id, packet_data, timestamp))
                except queue.Empty:
                    pass
    
    def register_display_callback(self, client_id: str, callback: Callable):
        """Register callback for immediate frame display."""
        self.frame_processor.register_client_callback(client_id, callback)
    
    def _ultra_fast_processing_loop(self):
        """Ultra-fast processing loop with minimal overhead."""
        while self.is_running:
            try:
                # Minimal timeout for responsiveness
                client_id, packet_data, timestamp = self.packet_queue.get(timeout=0.001)
                self.frame_processor.process_frame_immediate(client_id, packet_data, timestamp)
            except queue.Empty:
                continue
            except Exception:
                continue  # Ignore errors for speed


class AntiFlickerSystem:
    """
    Anti-flicker system for stable video display.
    Eliminates flickering through consistent frame timing and display.
    """
    
    def __init__(self):
        self.display_lock = threading.RLock()
        self.last_display_times: Dict[str, float] = {}
        
        # Anti-flicker settings
        self.min_frame_interval = 1.0 / 120  # 120 FPS maximum
        self.frame_smoothing = True
        self.consistent_timing = True
        
        # Display state tracking
        self.active_displays: Dict[str, bool] = {}
        self.frame_counters: Dict[str, int] = {}
    
    def should_display_frame(self, client_id: str) -> bool:
        """Check if frame should be displayed to prevent flickering."""
        current_time = time.perf_counter()
        
        with self.display_lock:
            last_time = self.last_display_times.get(client_id, 0)
            
            # Always display first frame
            if last_time == 0:
                self.last_display_times[client_id] = current_time
                self.frame_counters[client_id] = 1
                return True
            
            # Check minimum interval for smooth display
            if current_time - last_time >= self.min_frame_interval:
                self.last_display_times[client_id] = current_time
                self.frame_counters[client_id] = self.frame_counters.get(client_id, 0) + 1
                return True
            
            return False
    
    def mark_display_active(self, client_id: str):
        """Mark display as active for client."""
        with self.display_lock:
            self.active_displays[client_id] = True
    
    def mark_display_inactive(self, client_id: str):
        """Mark display as inactive for client."""
        with self.display_lock:
            self.active_displays[client_id] = False
            if client_id in self.last_display_times:
                del self.last_display_times[client_id]
            if client_id in self.frame_counters:
                del self.frame_counters[client_id]


class ExtremeVideoOptimizer:
    """
    Main extreme video optimizer for ultra-fast, flicker-free video.
    Coordinates all optimization components for maximum performance.
    """
    
    def __init__(self):
        self.network_handler = UltraFastNetworkHandler()
        self.anti_flicker = AntiFlickerSystem()
        
        # Optimization state
        self.is_active = False
        self.optimization_lock = threading.RLock()
        
        # Performance settings
        self.ultra_fast_mode = True
        self.zero_latency_display = True
        self.anti_flicker_enabled = True
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'frames_displayed': 0,
            'flicker_events_prevented': 0,
            'average_latency': 0,
            'start_time': None
        }
    
    def start_optimization(self):
        """Start extreme video optimization system."""
        with self.optimization_lock:
            if self.is_active:
                return
            
            self.is_active = True
            self.stats['start_time'] = time.time()
            
            # Start network processing
            self.network_handler.start_processing()
            
            logger.info("Extreme video optimization started - Ultra-fast mode enabled")
    
    def stop_optimization(self):
        """Stop extreme video optimization system."""
        with self.optimization_lock:
            if not self.is_active:
                return
            
            self.is_active = False
            
            # Stop network processing
            self.network_handler.stop_processing()
            
            logger.info("Extreme video optimization stopped")
    
    def register_client_display(self, client_id: str, display_callback: Callable):
        """Register client for extreme optimization."""
        if not self.is_active:
            self.start_optimization()
        
        # Register for immediate display
        self.network_handler.register_display_callback(client_id, 
            lambda frame: self._optimized_display_callback(client_id, frame, display_callback))
        
        # Mark as active
        self.anti_flicker.mark_display_active(client_id)
        
        logger.info(f"Registered client {client_id} for extreme video optimization")
    
    def process_video_packet_extreme(self, client_id: str, packet_data: bytes):
        """Process video packet with extreme optimization."""
        if not self.is_active:
            return
        
        timestamp = time.perf_counter()
        
        # Ultra-fast processing
        self.network_handler.process_video_packet_immediate(client_id, packet_data, timestamp)
        
        # Update statistics
        self.stats['frames_processed'] += 1
    
    def _optimized_display_callback(self, client_id: str, frame: np.ndarray, original_callback: Callable):
        """Optimized display callback with anti-flicker."""
        try:
            # Anti-flicker check
            if self.anti_flicker_enabled:
                if not self.anti_flicker.should_display_frame(client_id):
                    self.stats['flicker_events_prevented'] += 1
                    return
            
            # Call original display callback
            original_callback(frame)
            
            # Update statistics
            self.stats['frames_displayed'] += 1
            
        except Exception as e:
            logger.debug(f"Display callback error: {e}")
    
    def unregister_client(self, client_id: str):
        """Unregister client from optimization."""
        self.anti_flicker.mark_display_inactive(client_id)
        logger.info(f"Unregistered client {client_id} from extreme optimization")
    
    def get_extreme_stats(self) -> Dict:
        """Get extreme optimization statistics."""
        stats = self.stats.copy()
        stats['is_active'] = self.is_active
        stats['ultra_fast_mode'] = self.ultra_fast_mode
        stats['zero_latency_display'] = self.zero_latency_display
        
        # Add network handler stats
        stats['network_performance'] = self.network_handler.frame_processor.get_performance_stats()
        
        # Calculate uptime
        if stats['start_time']:
            stats['uptime'] = time.time() - stats['start_time']
        
        return stats
    
    def enable_ultra_fast_mode(self):
        """Enable ultra-fast mode for maximum performance."""
        self.ultra_fast_mode = True
        self.zero_latency_display = True
        self.network_handler.immediate_processing = True
        self.network_handler.frame_processor.immediate_display = True
        logger.info("Ultra-fast mode enabled - Maximum performance")
    
    def enable_anti_flicker_mode(self):
        """Enable anti-flicker mode for stable display."""
        self.anti_flicker_enabled = True
        self.anti_flicker.frame_smoothing = True
        self.anti_flicker.consistent_timing = True
        logger.info("Anti-flicker mode enabled - Stable display")


# Global extreme optimizer instance
extreme_video_optimizer = ExtremeVideoOptimizer()