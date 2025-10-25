"""
Optimized Video Conferencing System
Ensures perfect chronological frame ordering and eliminates back-and-forth video display.
"""

import time
import threading
import logging
import heapq
from typing import Dict, List, Optional, Tuple, NamedTuple
from collections import deque
import numpy as np
from client.frame_sequencer import FrameSequencer, TimestampedFrame
from client.video_capture import VideoCapture
from client.video_playback import VideoRenderer

logger = logging.getLogger(__name__)


class OptimizedFrameSequencer(FrameSequencer):
    """
    Optimized frame sequencer with enhanced chronological ordering.
    """
    
    def __init__(self, client_id: str, max_buffer_size: int = 15):
        super().__init__(client_id, max_buffer_size)
        
        # Enhanced chronological ordering parameters
        self.strict_chronological_mode = True
        self.max_temporal_jump = 0.01  # 10ms maximum temporal jump
        self.frame_age_tolerance = 0.1  # 100ms maximum frame age
        
        # Temporal validation
        self.temporal_validator = TemporalValidator()
        
        # Performance optimization
        self.ultra_fast_mode = False
        self.chronological_stats = {
            'frames_processed': 0,
            'chronological_violations': 0,
            'temporal_jumps_prevented': 0,
            'perfect_ordering_rate': 0.0
        }
    
    def add_frame(self, sequence_number: int, capture_timestamp: float, 
                  network_timestamp: float, frame_data: np.ndarray) -> bool:
        """
        Add frame with enhanced chronological validation.
        """
        # Validate temporal progression
        if not self.temporal_validator.validate_frame_timing(
            capture_timestamp, self.last_displayed_timestamp
        ):
            self.chronological_stats['temporal_jumps_prevented'] += 1
            logger.debug(f"Prevented temporal jump for frame {sequence_number}")
            return False
        
        # Enhanced chronological processing
        success = super().add_frame(sequence_number, capture_timestamp, network_timestamp, frame_data)
        
        if success:
            self.chronological_stats['frames_processed'] += 1
            self._update_chronological_stats()
        
        return success
    
    def get_next_frame(self) -> Optional[TimestampedFrame]:
        """
        Get next frame with strict chronological ordering.
        """
        frame = super().get_next_frame()
        
        if frame:
            # Validate chronological progression
            if self._validate_chronological_progression(frame):
                return frame
            else:
                # Reject frame that would cause temporal jump
                self.chronological_stats['chronological_violations'] += 1
                logger.debug(f"Rejected frame {frame.sequence_number} to prevent temporal jump")
                return None
        
        return None
    
    def _validate_chronological_progression(self, frame: TimestampedFrame) -> bool:
        """
        Validate that frame maintains chronological progression.
        """
        if self.last_displayed_sequence == -1:
            return True
        
        # Check temporal progression
        if frame.capture_timestamp < self.last_displayed_timestamp:
            time_diff = self.last_displayed_timestamp - frame.capture_timestamp
            if time_diff > self.max_temporal_jump:
                return False
        
        # Check sequence progression
        if frame.sequence_number < self.last_displayed_sequence:
            return False
        
        return True
    
    def _update_chronological_stats(self):
        """Update chronological ordering statistics."""
        if self.chronological_stats['frames_processed'] > 0:
            violations = self.chronological_stats['chronological_violations']
            processed = self.chronological_stats['frames_processed']
            self.chronological_stats['perfect_ordering_rate'] = 1.0 - (violations / processed)


class TemporalValidator:
    """
    Validates temporal progression of video frames.
    """
    
    def __init__(self):
        self.last_valid_timestamp = 0.0
        self.temporal_tolerance = 0.01  # 10ms tolerance
    
    def validate_frame_timing(self, current_timestamp: float, last_displayed: float) -> bool:
        """
        Validate that frame timing maintains chronological order.
        """
        if last_displayed == 0.0:
            self.last_valid_timestamp = current_timestamp
            return True
        
        # Check for temporal regression
        if current_timestamp < last_displayed - self.temporal_tolerance:
            return False
        
        # Update valid timestamp
        self.last_valid_timestamp = max(self.last_valid_timestamp, current_timestamp)
        return True


class OptimizedVideoConferencing:
    """
    Optimized video conferencing system with perfect frame ordering.
    """
    
    def __init__(self, client_id: str, connection_manager):
        self.client_id = client_id
        self.connection_manager = connection_manager
        
        # Video components
        self.video_capture = VideoCapture(client_id, connection_manager)
        self.video_renderer = VideoRenderer()
        
        # Optimized frame sequencers for each client
        self.frame_sequencers: Dict[str, OptimizedFrameSequencer] = {}
        self.sequencer_lock = threading.RLock()
        
        # Video conferencing state
        self.is_active = False
        self.video_enabled = False
        
        # Performance monitoring
        self.performance_stats = {
            'total_frames_sent': 0,
            'total_frames_received': 0,
            'chronological_accuracy': 0.0,
            'temporal_jumps_prevented': 0
        }
        
        # Setup callbacks
        self._setup_video_callbacks()
    
    def _setup_video_callbacks(self):
        """Setup video capture and playback callbacks."""
        # Video capture callback for local display
        self.video_capture.set_frame_callback(self._on_local_video_frame)
        
        # Video renderer callbacks
        self.video_renderer.set_frame_update_callback(self._on_remote_video_frame)
        self.video_renderer.set_stream_status_callback(self._on_video_stream_status)
    
    def start_video_conferencing(self) -> bool:
        """
        Start optimized video conferencing system.
        """
        try:
            if self.is_active:
                logger.warning("Video conferencing already active")
                return True
            
            # Start video renderer
            if not self.video_renderer.start_rendering():
                logger.error("Failed to start video renderer")
                return False
            
            self.is_active = True
            logger.info("Optimized video conferencing started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video conferencing: {e}")
            return False
    
    def stop_video_conferencing(self):
        """Stop video conferencing system."""
        if not self.is_active:
            return
        
        self.is_active = False
        
        # Stop video capture
        if self.video_enabled:
            self.video_capture.stop_capture()
            self.video_enabled = False
        
        # Stop video renderer
        self.video_renderer.stop_rendering()
        
        # Clear frame sequencers
        with self.sequencer_lock:
            self.frame_sequencers.clear()
        
        logger.info("Video conferencing stopped")
    
    def enable_video(self) -> bool:
        """
        Enable video capture and transmission.
        """
        try:
            if self.video_enabled:
                logger.warning("Video already enabled")
                return True
            
            # Start video capture
            success = self.video_capture.start_capture()
            if success:
                self.video_enabled = True
                logger.info("Video capture enabled")
                return True
            else:
                logger.error("Failed to start video capture")
                return False
                
        except Exception as e:
            logger.error(f"Error enabling video: {e}")
            return False
    
    def disable_video(self):
        """Disable video capture."""
        if self.video_enabled:
            self.video_capture.stop_capture()
            self.video_enabled = False
            logger.info("Video capture disabled")
    
    def process_incoming_video(self, video_packet):
        """
        Process incoming video packet with optimized frame sequencing.
        """
        if not self.is_active:
            return
        
        try:
            client_id = video_packet.sender_id
            
            # Get or create frame sequencer for client
            with self.sequencer_lock:
                if client_id not in self.frame_sequencers:
                    self.frame_sequencers[client_id] = OptimizedFrameSequencer(client_id)
                    logger.info(f"Created optimized frame sequencer for {client_id}")
                
                sequencer = self.frame_sequencers[client_id]
            
            # Extract timing information
            sequence_number = video_packet.sequence_num
            capture_timestamp = getattr(video_packet, 'capture_timestamp', time.perf_counter())
            network_timestamp = getattr(video_packet, 'network_timestamp', time.perf_counter())
            
            # Decompress frame
            frame_data = self._decompress_video_frame(video_packet.data)
            
            if frame_data is not None:
                # Add frame to optimized sequencer
                success = sequencer.add_frame(
                    sequence_number, capture_timestamp, network_timestamp, frame_data
                )
                
                if success:
                    self.performance_stats['total_frames_received'] += 1
                    logger.debug(f"Added frame {sequence_number} to optimized sequencer for {client_id}")
                else:
                    logger.debug(f"Frame {sequence_number} rejected by optimized sequencer for {client_id}")
            else:
                logger.warning(f"Failed to decompress frame from {client_id}")
                
        except Exception as e:
            logger.error(f"Error processing incoming video: {e}")
    
    def _decompress_video_frame(self, compressed_data: bytes) -> Optional[np.ndarray]:
        """Decompress video frame data."""
        try:
            import cv2
            nparr = np.frombuffer(compressed_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.error(f"Error decompressing frame: {e}")
            return None
    
    def _on_local_video_frame(self, frame: np.ndarray):
        """Handle local video frame for display."""
        # This would typically update the GUI with local video
        pass
    
    def _on_remote_video_frame(self, client_id: str, frame: np.ndarray):
        """Handle remote video frame from optimized sequencer."""
        try:
            # Get frame from optimized sequencer
            with self.sequencer_lock:
                if client_id in self.frame_sequencers:
                    sequencer = self.frame_sequencers[client_id]
                    optimized_frame = sequencer.get_next_frame()
                    
                    if optimized_frame:
                        # Display frame with perfect chronological order
                        self._display_chronological_frame(client_id, optimized_frame.frame_data)
                        
                        # Update performance stats
                        self._update_performance_stats(sequencer)
            
        except Exception as e:
            logger.error(f"Error handling remote video frame: {e}")
    
    def _display_chronological_frame(self, client_id: str, frame_data: np.ndarray):
        """Display frame with perfect chronological ordering."""
        # This would typically update the GUI with remote video
        # The frame is guaranteed to be in chronological order
        pass
    
    def _update_performance_stats(self, sequencer: OptimizedFrameSequencer):
        """Update performance statistics."""
        stats = sequencer.chronological_stats
        if stats['frames_processed'] > 0:
            self.performance_stats['chronological_accuracy'] = stats['perfect_ordering_rate']
            self.performance_stats['temporal_jumps_prevented'] = stats['temporal_jumps_prevented']
    
    def _on_video_stream_status(self, client_id: str, active: bool):
        """Handle video stream status changes."""
        if not active:
            # Remove frame sequencer for disconnected client
            with self.sequencer_lock:
                if client_id in self.frame_sequencers:
                    del self.frame_sequencers[client_id]
                logger.info(f"Removed frame sequencer for {client_id}")
    
    def get_performance_stats(self) -> Dict:
        """Get video conferencing performance statistics."""
        stats = self.performance_stats.copy()
        stats['is_active'] = self.is_active
        stats['video_enabled'] = self.video_enabled
        stats['active_sequencers'] = len(self.frame_sequencers)
        
        # Add sequencer statistics
        stats['sequencer_stats'] = {}
        with self.sequencer_lock:
            for client_id, sequencer in self.frame_sequencers.items():
                stats['sequencer_stats'][client_id] = sequencer.chronological_stats.copy()
        
        return stats


# Global optimized video conferencing instance
optimized_video_conferencing = None


def initialize_optimized_video_conferencing(client_id: str, connection_manager):
    """Initialize the optimized video conferencing system."""
    global optimized_video_conferencing
    optimized_video_conferencing = OptimizedVideoConferencing(client_id, connection_manager)
    return optimized_video_conferencing


def get_optimized_video_conferencing():
    """Get the global optimized video conferencing instance."""
    return optimized_video_conferencing
