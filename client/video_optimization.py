"""
Advanced video optimization module for stable, continuous streaming.
Implements frame buffering, adaptive bitrate control, and synchronization.
"""

import threading
import time
import logging
import queue
import statistics
from typing import Dict, List, Optional, Tuple, Deque
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class AdaptiveBitrateController:
    """
    Adaptive bitrate controller for maintaining optimal video quality
    based on network conditions and system performance.
    """
    
    def __init__(self):
        self.current_quality = 70  # Start with medium quality
        self.min_quality = 30
        self.max_quality = 95
        
        # Network metrics tracking
        self.packet_loss_history = deque(maxlen=50)
        self.latency_history = deque(maxlen=50)
        self.throughput_history = deque(maxlen=50)
        
        # Performance metrics
        self.frame_drop_history = deque(maxlen=30)
        self.encoding_time_history = deque(maxlen=30)
        
        # Adaptation parameters
        self.adaptation_interval = 2.0  # Adapt every 2 seconds
        self.last_adaptation_time = 0
        
        # Quality levels
        self.quality_levels = {
            'ultra_low': {'quality': 30, 'fps': 15, 'resolution_scale': 0.5},
            'low': {'quality': 40, 'fps': 20, 'resolution_scale': 0.7},
            'medium': {'quality': 60, 'fps': 25, 'resolution_scale': 0.8},
            'high': {'quality': 80, 'fps': 30, 'resolution_scale': 1.0},
            'ultra_high': {'quality': 95, 'fps': 30, 'resolution_scale': 1.0}
        }
        
        self.current_level = 'medium'
    
    def update_network_metrics(self, packet_loss: float, latency: float, throughput: float):
        """Update network performance metrics."""
        self.packet_loss_history.append(packet_loss)
        self.latency_history.append(latency)
        self.throughput_history.append(throughput)
    
    def update_performance_metrics(self, frame_drops: int, encoding_time: float):
        """Update system performance metrics."""
        self.frame_drop_history.append(frame_drops)
        self.encoding_time_history.append(encoding_time)
    
    def should_adapt(self) -> bool:
        """Check if adaptation should occur."""
        current_time = time.time()
        return (current_time - self.last_adaptation_time) >= self.adaptation_interval
    
    def adapt_quality(self) -> Dict:
        """Adapt video quality based on current conditions."""
        if not self.should_adapt():
            return self.quality_levels[self.current_level]
        
        self.last_adaptation_time = time.time()
        
        # Calculate average metrics
        avg_packet_loss = statistics.mean(self.packet_loss_history) if self.packet_loss_history else 0
        avg_latency = statistics.mean(self.latency_history) if self.latency_history else 0
        avg_frame_drops = statistics.mean(self.frame_drop_history) if self.frame_drop_history else 0
        avg_encoding_time = statistics.mean(self.encoding_time_history) if self.encoding_time_history else 0
        
        # Determine target quality level
        target_level = self.current_level
        
        # Degrade quality if network issues
        if avg_packet_loss > 0.05 or avg_latency > 100:  # 5% loss or 100ms latency
            if self.current_level == 'ultra_high':
                target_level = 'high'
            elif self.current_level == 'high':
                target_level = 'medium'
            elif self.current_level == 'medium':
                target_level = 'low'
            elif self.current_level == 'low':
                target_level = 'ultra_low'
        
        # Degrade quality if system performance issues
        elif avg_frame_drops > 2 or avg_encoding_time > 0.05:  # 2 drops or 50ms encoding
            if self.current_level in ['ultra_high', 'high']:
                target_level = 'medium'
            elif self.current_level == 'medium':
                target_level = 'low'
        
        # Improve quality if conditions are good
        elif avg_packet_loss < 0.01 and avg_latency < 30 and avg_frame_drops < 1:
            if self.current_level == 'ultra_low':
                target_level = 'low'
            elif self.current_level == 'low':
                target_level = 'medium'
            elif self.current_level == 'medium':
                target_level = 'high'
            elif self.current_level == 'high' and avg_encoding_time < 0.02:
                target_level = 'ultra_high'
        
        if target_level != self.current_level:
            logger.info(f"Adapting video quality: {self.current_level} -> {target_level}")
            self.current_level = target_level
        
        return self.quality_levels[self.current_level]


class FrameBuffer:
    """
    Advanced frame buffer with jitter compensation and smooth playback.
    """
    
    def __init__(self, client_id: str, target_buffer_size: int = 1):  # Ultra-low latency: 1 frame buffer
        self.client_id = client_id
        self.target_buffer_size = target_buffer_size
        self.max_buffer_size = max(target_buffer_size * 2, 2)  # Minimum 2 frames
        
        # Ultra-low latency mode for LAN
        self.ultra_low_latency = True  # Enable for LAN networks
        
        # Frame storage
        self.frames: Deque[Dict] = deque(maxlen=self.max_buffer_size)
        self.lock = threading.RLock()
        
        # Timing and synchronization - optimized for immediate display
        self.last_frame_time = 0
        self.frame_interval = 1.0 / 60  # Target 60 FPS for ultra-smooth
        self.jitter_buffer = deque(maxlen=5)  # Smaller jitter buffer
        
        # Statistics
        self.stats = {
            'frames_added': 0,
            'frames_dropped': 0,
            'buffer_underruns': 0,
            'buffer_overruns': 0,
            'average_jitter': 0
        }
    
    def add_frame(self, frame_data: np.ndarray, timestamp: float, sequence: int) -> bool:
        """Add frame to buffer with jitter compensation."""
        with self.lock:
            current_time = time.time()
            
            # Calculate jitter
            if self.last_frame_time > 0:
                expected_time = self.last_frame_time + self.frame_interval
                jitter = abs(current_time - expected_time)
                self.jitter_buffer.append(jitter)
                
                # Update average jitter
                if self.jitter_buffer:
                    self.stats['average_jitter'] = statistics.mean(self.jitter_buffer)
            
            self.last_frame_time = current_time
            
            # Check for buffer overrun
            if len(self.frames) >= self.max_buffer_size:
                # Drop oldest frame
                self.frames.popleft()
                self.stats['buffer_overruns'] += 1
                logger.debug(f"Buffer overrun for {self.client_id}, dropped oldest frame")
            
            # Add new frame
            frame_info = {
                'data': frame_data,
                'timestamp': timestamp,
                'sequence': sequence,
                'arrival_time': current_time
            }
            
            self.frames.append(frame_info)
            self.stats['frames_added'] += 1
            
            return True
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get next frame for playback with ultra-low latency."""
        with self.lock:
            if self.ultra_low_latency:
                # Ultra-low latency mode: return immediately if any frame available
                if len(self.frames) > 0:
                    frame_info = self.frames.popleft()
                    return frame_info['data']
                return None
            else:
                # Standard buffering mode
                if len(self.frames) < self.target_buffer_size:
                    # Buffer underrun - wait for more frames
                    if len(self.frames) == 0:
                        self.stats['buffer_underruns'] += 1
                    return None
                
                # Get oldest frame
                frame_info = self.frames.popleft()
                return frame_info['data']
    
    def get_buffer_health(self) -> Dict:
        """Get buffer health metrics."""
        with self.lock:
            return {
                'current_size': len(self.frames),
                'target_size': self.target_buffer_size,
                'health_ratio': len(self.frames) / self.target_buffer_size if self.target_buffer_size > 0 else 0,
                'stats': self.stats.copy()
            }
    
    def adjust_target_size(self, new_size: int):
        """Dynamically adjust target buffer size."""
        with self.lock:
            self.target_buffer_size = max(1, min(new_size, self.max_buffer_size // 2))
            logger.debug(f"Adjusted buffer size for {self.client_id}: {self.target_buffer_size}")


class SynchronizationManager:
    """
    Manages synchronization between capture, encoding, transmission, and decoding.
    """
    
    def __init__(self):
        self.frame_timings = {}  # client_id -> timing info
        self.sync_lock = threading.RLock()
        
        # Synchronization parameters
        self.max_sync_drift = 0.1  # 100ms max drift
        self.sync_adjustment_rate = 0.1  # 10% adjustment per correction
        
    def register_frame_timing(self, client_id: str, stage: str, timestamp: float, sequence: int):
        """Register timing for different pipeline stages."""
        with self.sync_lock:
            if client_id not in self.frame_timings:
                self.frame_timings[client_id] = {}
            
            if sequence not in self.frame_timings[client_id]:
                self.frame_timings[client_id][sequence] = {}
            
            self.frame_timings[client_id][sequence][stage] = timestamp
            
            # Clean old entries (keep last 50 frames)
            if len(self.frame_timings[client_id]) > 50:
                oldest_seq = min(self.frame_timings[client_id].keys())
                del self.frame_timings[client_id][oldest_seq]
    
    def calculate_pipeline_latency(self, client_id: str) -> Dict:
        """Calculate end-to-end pipeline latency."""
        with self.sync_lock:
            if client_id not in self.frame_timings:
                return {}
            
            recent_frames = list(self.frame_timings[client_id].values())[-10:]  # Last 10 frames
            
            latencies = {
                'capture_to_encode': [],
                'encode_to_transmit': [],
                'transmit_to_decode': [],
                'decode_to_display': [],
                'end_to_end': []
            }
            
            for frame_timing in recent_frames:
                if all(stage in frame_timing for stage in ['capture', 'encode', 'transmit', 'decode', 'display']):
                    latencies['capture_to_encode'].append(frame_timing['encode'] - frame_timing['capture'])
                    latencies['encode_to_transmit'].append(frame_timing['transmit'] - frame_timing['encode'])
                    latencies['transmit_to_decode'].append(frame_timing['decode'] - frame_timing['transmit'])
                    latencies['decode_to_display'].append(frame_timing['display'] - frame_timing['decode'])
                    latencies['end_to_end'].append(frame_timing['display'] - frame_timing['capture'])
            
            # Calculate averages
            avg_latencies = {}
            for stage, times in latencies.items():
                if times:
                    avg_latencies[stage] = statistics.mean(times)
                else:
                    avg_latencies[stage] = 0
            
            return avg_latencies
    
    def get_sync_adjustment(self, client_id: str) -> float:
        """Calculate synchronization adjustment for smooth playback."""
        latencies = self.calculate_pipeline_latency(client_id)
        
        if not latencies or 'end_to_end' not in latencies:
            return 0.0
        
        end_to_end = latencies['end_to_end']
        
        # If latency is too high, suggest speedup
        if end_to_end > self.max_sync_drift:
            return -self.sync_adjustment_rate  # Speed up playback
        
        # If latency is too low, suggest slowdown
        elif end_to_end < -self.max_sync_drift:
            return self.sync_adjustment_rate  # Slow down playback
        
        return 0.0  # No adjustment needed


class VideoStreamOptimizer:
    """
    Main video stream optimizer coordinating all optimization components.
    """
    
    def __init__(self):
        self.bitrate_controller = AdaptiveBitrateController()
        self.frame_buffers: Dict[str, FrameBuffer] = {}
        self.sync_manager = SynchronizationManager()
        
        # Optimization state
        self.is_optimizing = False
        self.optimization_thread: Optional[threading.Thread] = None
        
        # Performance monitoring
        self.performance_metrics = {
            'total_frames_processed': 0,
            'frames_dropped': 0,
            'average_latency': 0,
            'quality_adaptations': 0
        }
    
    def start_optimization(self):
        """Start the optimization system."""
        if self.is_optimizing:
            return
        
        self.is_optimizing = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        logger.info("Video stream optimization started")
    
    def stop_optimization(self):
        """Stop the optimization system."""
        self.is_optimizing = False
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=1.0)
        logger.info("Video stream optimization stopped")
    
    def register_client(self, client_id: str, target_buffer_size: int = 3):
        """Register a new client for optimization."""
        if client_id not in self.frame_buffers:
            self.frame_buffers[client_id] = FrameBuffer(client_id, target_buffer_size)
            logger.info(f"Registered client {client_id} for video optimization")
    
    def unregister_client(self, client_id: str):
        """Unregister a client from optimization."""
        if client_id in self.frame_buffers:
            del self.frame_buffers[client_id]
            logger.info(f"Unregistered client {client_id} from video optimization")
    
    def add_frame(self, client_id: str, frame_data: np.ndarray, timestamp: float, sequence: int) -> bool:
        """Add frame to client's buffer."""
        if client_id not in self.frame_buffers:
            self.register_client(client_id)
        
        # Register timing
        self.sync_manager.register_frame_timing(client_id, 'decode', timestamp, sequence)
        
        return self.frame_buffers[client_id].add_frame(frame_data, timestamp, sequence)
    
    def get_frame(self, client_id: str) -> Optional[np.ndarray]:
        """Get optimized frame for display."""
        if client_id not in self.frame_buffers:
            return None
        
        frame = self.frame_buffers[client_id].get_frame()
        
        if frame is not None:
            # Register display timing
            current_time = time.time()
            # Note: sequence number would need to be tracked separately for this to work properly
            # For now, we'll use a placeholder
            self.sync_manager.register_frame_timing(client_id, 'display', current_time, 0)
        
        return frame
    
    def get_quality_settings(self) -> Dict:
        """Get current adaptive quality settings."""
        return self.bitrate_controller.adapt_quality()
    
    def update_network_conditions(self, packet_loss: float, latency: float, throughput: float):
        """Update network condition metrics."""
        self.bitrate_controller.update_network_metrics(packet_loss, latency, throughput)
    
    def update_performance_metrics(self, frame_drops: int, encoding_time: float):
        """Update system performance metrics."""
        self.bitrate_controller.update_performance_metrics(frame_drops, encoding_time)
    
    def _optimization_loop(self):
        """Main optimization loop."""
        logger.info("Video optimization loop started")
        
        while self.is_optimizing:
            try:
                # Monitor buffer health and adjust
                for client_id, buffer in self.frame_buffers.items():
                    health = buffer.get_buffer_health()
                    
                    # Adjust buffer size based on health
                    if health['health_ratio'] < 0.5:  # Buffer too small
                        new_size = min(buffer.target_buffer_size + 1, 5)
                        buffer.adjust_target_size(new_size)
                    elif health['health_ratio'] > 1.5:  # Buffer too large
                        new_size = max(buffer.target_buffer_size - 1, 2)
                        buffer.adjust_target_size(new_size)
                
                # Sleep for optimization interval
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                break
        
        logger.info("Video optimization loop ended")
    
    def get_optimization_stats(self) -> Dict:
        """Get comprehensive optimization statistics."""
        stats = {
            'bitrate_controller': {
                'current_level': self.bitrate_controller.current_level,
                'current_quality': self.bitrate_controller.current_quality,
                'adaptation_count': len(self.bitrate_controller.packet_loss_history)
            },
            'frame_buffers': {},
            'performance_metrics': self.performance_metrics.copy()
        }
        
        # Add buffer stats for each client
        for client_id, buffer in self.frame_buffers.items():
            stats['frame_buffers'][client_id] = buffer.get_buffer_health()
        
        return stats


# Global optimizer instance
video_optimizer = VideoStreamOptimizer()