"""
Frame Sequencing System
Ensures frames are displayed in strict chronological order with proper timestamping,
ordering, and buffering mechanisms for smooth, correctly ordered frame rendering.
"""

import threading
import time
import logging
import heapq
from typing import Dict, List, Optional, Tuple, NamedTuple
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class TimestampedFrame(NamedTuple):
    """Represents a frame with comprehensive timing information."""
    sequence_number: int
    capture_timestamp: float  # When frame was captured
    network_timestamp: float  # When frame was sent over network
    arrival_timestamp: float  # When frame arrived at receiver
    frame_data: np.ndarray
    client_id: str


class FrameSequencer:
    """
    Advanced frame sequencer that ensures chronological order display.
    """
    
    def __init__(self, client_id: str, max_buffer_size: int = 10):
        self.client_id = client_id
        self.max_buffer_size = max_buffer_size
        
        # Frame ordering structures
        self.frame_heap = []  # Min-heap ordered by capture_timestamp
        self.sequence_buffer = {}  # sequence_number -> TimestampedFrame
        self.last_displayed_sequence = -1
        self.last_displayed_timestamp = 0.0
        
        # Timing management
        self.base_timestamp = None  # Reference timestamp for synchronization
        self.clock_offset = 0.0  # Offset between sender and receiver clocks
        self.jitter_buffer_size = 2  # Reduced buffer size for better performance
        
        # Sequencing parameters - optimized for performance
        self.max_frame_age = 0.5  # Reduced age limit for better performance (seconds)
        self.max_sequence_gap = 5  # Reduced gap tolerance for faster processing
        self.reorder_timeout = 0.05  # Reduced timeout for better performance (seconds)
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_displayed': 0,
            'frames_dropped_old': 0,
            'frames_dropped_duplicate': 0,
            'frames_reordered': 0,
            'sequence_gaps': 0,
            'average_jitter': 0.0
        }
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Jitter calculation
        self.jitter_samples = deque(maxlen=50)
        self.last_arrival_time = 0.0
    
    def add_frame(self, sequence_number: int, capture_timestamp: float, 
                  network_timestamp: float, frame_data: np.ndarray) -> bool:
        """
        Add frame to sequencer with comprehensive timestamp information.
        
        Args:
            sequence_number: Frame sequence number from sender
            capture_timestamp: When frame was captured at sender
            network_timestamp: When frame was sent over network
            frame_data: Frame image data
            
        Returns:
            bool: True if frame was accepted, False if dropped
        """
        arrival_timestamp = time.time()
        
        with self.lock:
            # Update statistics
            self.stats['frames_received'] += 1
            
            # Calculate jitter
            if self.last_arrival_time > 0:
                inter_arrival_time = arrival_timestamp - self.last_arrival_time
                expected_interval = 1.0 / 30  # Assume 30 FPS
                jitter = abs(inter_arrival_time - expected_interval)
                self.jitter_samples.append(jitter)
                
                if self.jitter_samples:
                    self.stats['average_jitter'] = sum(self.jitter_samples) / len(self.jitter_samples)
            
            self.last_arrival_time = arrival_timestamp
            
            # Initialize base timestamp if first frame
            if self.base_timestamp is None:
                self.base_timestamp = capture_timestamp
                self.clock_offset = arrival_timestamp - network_timestamp
                logger.info(f"Initialized frame sequencer for {self.client_id}, clock offset: {self.clock_offset:.3f}s")
            
            # Check for duplicate frames
            if sequence_number in self.sequence_buffer:
                self.stats['frames_dropped_duplicate'] += 1
                logger.debug(f"Dropped duplicate frame {sequence_number} for {self.client_id}")
                return False
            
            # Check frame age
            frame_age = arrival_timestamp - (network_timestamp + self.clock_offset)
            if frame_age > self.max_frame_age:
                self.stats['frames_dropped_old'] += 1
                logger.debug(f"Dropped old frame {sequence_number} (age: {frame_age:.3f}s) for {self.client_id}")
                return False
            
            # Create timestamped frame
            timestamped_frame = TimestampedFrame(
                sequence_number=sequence_number,
                capture_timestamp=capture_timestamp,
                network_timestamp=network_timestamp,
                arrival_timestamp=arrival_timestamp,
                frame_data=frame_data,
                client_id=self.client_id
            )
            
            # Add to sequence buffer
            self.sequence_buffer[sequence_number] = timestamped_frame
            
            # Add to heap ordered by capture timestamp for chronological processing
            heapq.heappush(self.frame_heap, (capture_timestamp, sequence_number))
            
            # Sort heap to ensure strict chronological order
            if len(self.frame_heap) > 1:
                # Re-heapify to maintain chronological order
                heapq.heapify(self.frame_heap)
            
            # Maintain buffer size
            self._cleanup_old_frames()
            
            logger.debug(f"Added frame {sequence_number} to sequencer for {self.client_id}")
            return True
    
    def get_next_frame(self) -> Optional[TimestampedFrame]:
        """
        Get the next frame in strict chronological order with enhanced synchronization.
        
        Returns:
            TimestampedFrame: Next frame to display, or None if no frame ready
        """
        with self.lock:
            if not self.frame_heap:
                return None
            
            current_time = time.time()
            
            # Process frames in strict chronological order
            while self.frame_heap:
                capture_timestamp, sequence_number = heapq.heappop(self.frame_heap)
                
                if sequence_number not in self.sequence_buffer:
                    continue  # Frame was already processed or cleaned up
                
                frame = self.sequence_buffer[sequence_number]
                
                # Enhanced chronological ordering check
                if self._is_frame_ready_for_synchronized_display(frame, current_time):
                    # Remove from buffer
                    del self.sequence_buffer[sequence_number]
                    
                    # Update display tracking with enhanced synchronization
                    self.last_displayed_sequence = max(self.last_displayed_sequence, frame.sequence_number)
                    self.last_displayed_timestamp = max(self.last_displayed_timestamp, capture_timestamp)
                    self.stats['frames_displayed'] += 1
                    
                    logger.debug(f"Displaying synchronized frame {sequence_number} for {self.client_id}")
                    return frame
                else:
                    # Frame not ready yet, put it back and wait briefly
                    heapq.heappush(self.frame_heap, (capture_timestamp, sequence_number))
                    return None
            
            return None
    def _is_frame_ready_for_synchronized_display(self, frame: TimestampedFrame, current_time: float) -> bool:
        """
        Enhanced chronological readiness check for synchronized display.
        
        Args:
            frame: Frame to check
            current_time: Current system time
            
        Returns:
            bool: True if frame is ready for synchronized display
        """
        # Always display if it's the first frame
        if self.last_displayed_sequence == -1:
            return True
        
        # STRICT CHRONOLOGICAL ORDERING: Prevent any back-and-forth display
        if frame.capture_timestamp < self.last_displayed_timestamp:
            # Frame is older than last displayed - reject to prevent temporal jumping
            time_diff = self.last_displayed_timestamp - frame.capture_timestamp
            if time_diff > 0.005:  # More than 5ms difference - reject old frames
                logger.debug(f"Rejecting old frame {frame.sequence_number} (time diff: {time_diff:.3f}s) to prevent back-and-forth")
                self.stats['frames_dropped_old'] += 1
                return False
        
        # Check sequence order for additional validation
        sequence_gap = frame.sequence_number - self.last_displayed_sequence
        
        # Frame is next in sequence - always ready
        if sequence_gap == 1:
            return True
        
        # Frame is ahead in sequence - handle gaps intelligently
        if sequence_gap > 1:
            # For small gaps (1-2), wait briefly for missing frames
            if sequence_gap <= 2:
                wait_time = current_time - frame.arrival_timestamp
                if wait_time < 0.01:  # Wait up to 10ms for small gaps
                    return False
            
            # For larger gaps or after timeout, display frame to maintain flow
            self.stats['sequence_gaps'] += max(0, sequence_gap - 1)
            return True
        
        # Frame is behind in sequence but chronologically newer
        if sequence_gap <= 0:
            # Only display if timestamp is significantly newer (prevent duplicates)
            return frame.capture_timestamp > self.last_displayed_timestamp + 0.001  # 1ms buffer
        
        return True
    
    def _is_frame_chronologically_ready(self, frame: TimestampedFrame, current_time: float) -> bool:
        """
        Check if frame is ready for chronological display to prevent back-and-forth video.
        
        Args:
            frame: Frame to check
            current_time: Current system time
            
        Returns:
            bool: True if frame is ready for chronological display
        """
        # Always display if it's the first frame
        if self.last_displayed_sequence == -1:
            return True
        
        # Check if frame is chronologically after the last displayed frame
        if frame.capture_timestamp < self.last_displayed_timestamp:
            # Frame is older than last displayed - only allow if very close in time
            time_diff = self.last_displayed_timestamp - frame.capture_timestamp
            if time_diff > 0.033:  # More than one frame interval (30 FPS)
                return False  # Skip old frames to prevent back-and-forth
        
        # Check sequence order for additional validation
        sequence_gap = frame.sequence_number - self.last_displayed_sequence
        
        # Frame is next in sequence - always ready
        if sequence_gap == 1:
            return True
        
        # Frame is ahead in sequence
        if sequence_gap > 1:
            # Check if we should wait for missing frames
            wait_time = current_time - frame.arrival_timestamp
            
            # For small gaps, wait briefly for missing frames
            if sequence_gap <= 3 and wait_time < 0.05:  # Wait up to 50ms for small gaps
                return False
            
            # For larger gaps or after timeout, display the frame
            if sequence_gap > 3 or wait_time >= 0.05:
                self.stats['sequence_gaps'] += max(0, sequence_gap - 1)
                return True
        
        # Frame is behind in sequence but chronologically newer
        if sequence_gap <= 0:
            # Only display if timestamp is significantly newer
            return frame.capture_timestamp > self.last_displayed_timestamp
        
        return True
    
    def _is_frame_ready_for_display_ultra_fast(self, frame: TimestampedFrame) -> bool:
        """
        Ultra-fast frame readiness check for maximum performance.
        
        Args:
            frame: Frame to check
            
        Returns:
            bool: True if frame is ready for display
        """
        # Always display if it's the first frame
        if self.last_displayed_sequence == -1:
            return True
        
        # Check sequence order
        sequence_gap = frame.sequence_number - self.last_displayed_sequence
        
        # Frame is next in sequence
        if sequence_gap == 1:
            return True
        
        # For maximum performance, only wait for very small gaps
        if sequence_gap == 2:
            current_time = time.time()
            wait_time = current_time - frame.arrival_timestamp
            return wait_time >= 0.005  # Only 5ms wait maximum
        
        # Display all other frames immediately
        return True
    
    def _is_frame_ready_for_display_fast(self, frame: TimestampedFrame) -> bool:
        """
        Fast frame readiness check for maximum performance.
        
        Args:
            frame: Frame to check
            
        Returns:
            bool: True if frame is ready for display
        """
        # Always display if it's the first frame
        if self.last_displayed_sequence == -1:
            return True
        
        # Check sequence order
        sequence_gap = frame.sequence_number - self.last_displayed_sequence
        
        # Frame is next in sequence or close enough
        if sequence_gap == 1:
            return True
        
        # For performance, be more lenient with gaps
        if sequence_gap > 1 and sequence_gap <= 3:
            # Extremely short timeout for performance
            current_time = time.time()
            wait_time = current_time - frame.arrival_timestamp
            
            if wait_time >= 0.01:  # Only 10ms wait maximum
                self.stats['sequence_gaps'] += sequence_gap - 1
                return True
            
            return False
        
        # Display frame if gap is large (don't wait)
        if sequence_gap > 3:
            return True
        
        # Frame is older - display if timestamp is reasonable
        if sequence_gap <= 0:
            time_diff = frame.capture_timestamp - self.last_displayed_timestamp
            return time_diff > -0.05  # Allow frames up to 50ms old
        
        return False
    
    def _is_frame_ready_for_display(self, frame: TimestampedFrame) -> bool:
        """
        Check if frame is ready for display based on improved sequencing rules.
        
        Args:
            frame: Frame to check
            
        Returns:
            bool: True if frame is ready for display
        """
        # Always display if it's the first frame
        if self.last_displayed_sequence == -1:
            return True
        
        # Check sequence order
        sequence_gap = frame.sequence_number - self.last_displayed_sequence
        
        # Frame is next in sequence
        if sequence_gap == 1:
            return True
        
        # Frame is out of order but within acceptable gap
        if sequence_gap > 1 and sequence_gap <= self.max_sequence_gap:
            # Check if we've waited long enough for missing frames
            current_time = time.time()
            wait_time = current_time - frame.arrival_timestamp
            
            # Adaptive timeout based on jitter
            adaptive_timeout = min(self.reorder_timeout, 0.05)  # Max 50ms for performance
            
            if wait_time >= adaptive_timeout:
                # Timeout exceeded, display frame and mark gap
                self.stats['sequence_gaps'] += sequence_gap - 1
                logger.debug(f"Sequence gap detected for {self.client_id}: {self.last_displayed_sequence} -> {frame.sequence_number}")
                return True
            
            return False  # Wait longer for missing frames
        
        # Frame is too far out of order, display it anyway for performance
        if sequence_gap > self.max_sequence_gap:
            logger.debug(f"Large sequence gap for {self.client_id}: {self.last_displayed_sequence} -> {frame.sequence_number}")
            return True
        
        # Frame is older than last displayed (late arrival)
        if sequence_gap <= 0:
            # Display if timestamp is newer or if it's close enough
            time_diff = frame.capture_timestamp - self.last_displayed_timestamp
            return time_diff > -0.1  # Allow frames up to 100ms old
        
        return False
    
    def _cleanup_old_frames(self):
        """Clean up old frames to maintain buffer size."""
        current_time = time.time()
        
        # Remove frames that are too old
        old_sequences = []
        for seq, frame in self.sequence_buffer.items():
            frame_age = current_time - frame.arrival_timestamp
            if frame_age > self.max_frame_age:
                old_sequences.append(seq)
        
        for seq in old_sequences:
            if seq in self.sequence_buffer:
                del self.sequence_buffer[seq]
                self.stats['frames_dropped_old'] += 1
        
        # Remove old sequences from heap (will be skipped during pop)
        if len(self.sequence_buffer) > self.max_buffer_size:
            # Keep only the most recent frames
            sorted_frames = sorted(self.sequence_buffer.items(), 
                                 key=lambda x: x[1].capture_timestamp, reverse=True)
            
            frames_to_keep = sorted_frames[:self.max_buffer_size]
            sequences_to_keep = {seq for seq, _ in frames_to_keep}
            
            # Remove excess frames
            for seq in list(self.sequence_buffer.keys()):
                if seq not in sequences_to_keep:
                    del self.sequence_buffer[seq]
    
    def get_buffer_status(self) -> Dict:
        """Get current buffer status and statistics."""
        with self.lock:
            return {
                'client_id': self.client_id,
                'buffer_size': len(self.sequence_buffer),
                'heap_size': len(self.frame_heap),
                'last_displayed_sequence': self.last_displayed_sequence,
                'clock_offset': self.clock_offset,
                'stats': self.stats.copy()
            }
    
    def reset(self):
        """Reset sequencer state."""
        with self.lock:
            self.frame_heap.clear()
            self.sequence_buffer.clear()
            self.last_displayed_sequence = -1
            self.last_displayed_timestamp = 0.0
            self.base_timestamp = None
            self.clock_offset = 0.0
            
            # Reset statistics
            for key in self.stats:
                if key == 'average_jitter':
                    self.stats[key] = 0.0
                else:
                    self.stats[key] = 0
            
            self.jitter_samples.clear()
            logger.info(f"Reset frame sequencer for {self.client_id}")


class FrameSequencingManager:
    """
    Manages frame sequencers for multiple clients.
    """
    
    def __init__(self):
        self.sequencers: Dict[str, FrameSequencer] = {}
        self.manager_lock = threading.RLock()
        
        # Global sequencing parameters
        self.global_sync_enabled = True
        self.global_base_timestamp = None
        
        # Processing thread
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        
        # Frame callbacks
        self.frame_callbacks: Dict[str, callable] = {}
    
    def register_client(self, client_id: str, frame_callback: callable, 
                       max_buffer_size: int = 10):
        """
        Register a client for frame sequencing.
        
        Args:
            client_id: Client identifier
            frame_callback: Callback function for displaying frames
            max_buffer_size: Maximum buffer size for this client
        """
        with self.manager_lock:
            if client_id not in self.sequencers:
                self.sequencers[client_id] = FrameSequencer(client_id, max_buffer_size)
                self.frame_callbacks[client_id] = frame_callback
                
                logger.info(f"Registered frame sequencer for client {client_id}")
                
                # Start processing thread if not already running
                if not self.is_processing:
                    self._start_processing()
    
    def unregister_client(self, client_id: str):
        """Unregister a client from frame sequencing."""
        with self.manager_lock:
            if client_id in self.sequencers:
                del self.sequencers[client_id]
            if client_id in self.frame_callbacks:
                del self.frame_callbacks[client_id]
                
            logger.info(f"Unregistered frame sequencer for client {client_id}")
    
    def add_frame(self, client_id: str, sequence_number: int, 
                  capture_timestamp: float, network_timestamp: float, 
                  frame_data: np.ndarray) -> bool:
        """
        Add frame to appropriate sequencer.
        
        Args:
            client_id: Client identifier
            sequence_number: Frame sequence number
            capture_timestamp: When frame was captured
            network_timestamp: When frame was sent
            frame_data: Frame image data
            
        Returns:
            bool: True if frame was accepted
        """
        with self.manager_lock:
            if client_id not in self.sequencers:
                logger.warning(f"No sequencer registered for client {client_id}")
                return False
            
            # Initialize global base timestamp if needed
            if self.global_base_timestamp is None and self.global_sync_enabled:
                self.global_base_timestamp = capture_timestamp
                logger.info(f"Set global base timestamp: {self.global_base_timestamp}")
            
            return self.sequencers[client_id].add_frame(
                sequence_number, capture_timestamp, network_timestamp, frame_data
            )
    
    def _start_processing(self):
        """Start frame processing thread."""
        self.is_processing = True
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Started frame sequencing processing thread")
    
    def _processing_loop(self):
        """Main processing loop for frame sequencing with maximum performance."""
        while self.is_processing:
            try:
                frames_processed = 0
                
                with self.manager_lock:
                    # Process frames for each client
                    for client_id, sequencer in self.sequencers.items():
                        # Process many frames per client per loop for maximum performance
                        for _ in range(10):  # Process up to 10 frames per client per loop
                            frame = sequencer.get_next_frame()
                            
                            if frame and client_id in self.frame_callbacks:
                                try:
                                    # Call frame display callback
                                    self.frame_callbacks[client_id](frame.frame_data)
                                    frames_processed += 1
                                except Exception as e:
                                    logger.error(f"Error in frame callback for {client_id}: {e}")
                            else:
                                break  # No more frames for this client
                
                # Minimal sleep for maximum throughput
                if frames_processed > 0:
                    # High activity - maximum speed
                    time.sleep(1.0 / 240)  # 240 FPS for maximum throughput
                else:
                    # Low activity - still fast
                    time.sleep(1.0 / 120)  # 120 FPS for normal operation
                
            except Exception as e:
                logger.error(f"Error in frame sequencing loop: {e}")
                time.sleep(0.001)  # Minimal error recovery time
    
    def stop_processing(self):
        """Stop frame processing."""
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        logger.info("Stopped frame sequencing processing")
    
    def get_all_status(self) -> Dict:
        """Get status for all sequencers."""
        with self.manager_lock:
            return {
                client_id: sequencer.get_buffer_status()
                for client_id, sequencer in self.sequencers.items()
            }
    
    def reset_all(self):
        """Reset all sequencers."""
        with self.manager_lock:
            for sequencer in self.sequencers.values():
                sequencer.reset()
            
            self.global_base_timestamp = None
            logger.info("Reset all frame sequencers")


# Global frame sequencing manager
frame_sequencing_manager = FrameSequencingManager()