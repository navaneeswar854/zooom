"""
Video playback and rendering module for the collaboration client.
Handles incoming video stream reception, decompression, and display.
"""

import cv2
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
import numpy as np
from collections import deque
from common.messages import UDPPacket
from client.video_optimization import video_optimizer
from client.extreme_video_optimizer import extreme_video_optimizer
from client.stable_video_system import stability_manager
from client.frame_sequencer import frame_sequencing_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoRenderer:
    """
    Video rendering component for displaying incoming video streams.
    
    Handles:
    - Video stream reception and decompression
    - Multiple video feed management
    - Frame buffering and synchronization
    """
    
    def __init__(self):
        """Initialize the video renderer."""
        # Video streams from different clients
        self.video_streams: Dict[str, Dict[str, Any]] = {}  # client_id -> stream info
        
        # Frame buffers for each client
        self.frame_buffers: Dict[str, deque] = {}  # client_id -> frame buffer
        self.max_buffer_size = 5  # Keep last 5 frames per client
        
        # Rendering state
        self.is_rendering = False
        self.render_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Callbacks
        self.frame_update_callback: Optional[Callable[[str, np.ndarray], None]] = None
        self.stream_status_callback: Optional[Callable[[str, bool], None]] = None
        
        # Statistics
        self.stats = {
            'total_frames_received': 0,
            'total_frames_rendered': 0,
            'active_video_streams': 0,
            'decode_errors': 0,
            'render_start_time': None
        }
    
    def set_frame_update_callback(self, callback: Callable[[str, np.ndarray], None]):
        """
        Set callback for frame updates.
        
        Args:
            callback: Function to call with (client_id, frame) when new frame is available
        """
        self.frame_update_callback = callback
    
    def set_stream_status_callback(self, callback: Callable[[str, bool], None]):
        """
        Set callback for stream status changes.
        
        Args:
            callback: Function to call with (client_id, active) when stream status changes
        """
        self.stream_status_callback = callback
    
    def start_rendering(self) -> bool:
        """
        Start the video rendering system.
        
        Returns:
            bool: True if rendering started successfully
        """
        if self.is_rendering:
            logger.warning("Video rendering already running")
            return True
        
        try:
            self.is_rendering = True
            self.stats['render_start_time'] = time.time()
            
            # Start rendering thread
            self.render_thread = threading.Thread(
                target=self._render_loop,
                daemon=True
            )
            self.render_thread.start()
            
            logger.info("Video rendering started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video rendering: {e}")
            self.is_rendering = False
            return False
    
    def stop_rendering(self):
        """Stop the video rendering system."""
        if not self.is_rendering:
            return
        
        self.is_rendering = False
        
        # Wait for render thread to finish
        if self.render_thread and self.render_thread.is_alive():
            self.render_thread.join(timeout=1.0)
        
        # Clear all buffers
        with self._lock:
            self.video_streams.clear()
            self.frame_buffers.clear()
        
        logger.info("Video rendering stopped")
    
    def process_video_packet(self, video_packet: UDPPacket):
        """
        Process incoming video packet with frame sequencing for chronological order.
        
        Args:
            video_packet: UDP packet containing compressed video data
        """
        if not self.is_rendering:
            return
        
        try:
            client_id = video_packet.sender_id
            
            # Initialize stream if new with sequencing
            with self._lock:
                if client_id not in self.video_streams:
                    self.video_streams[client_id] = {
                        'last_packet_time': time.time(),
                        'packets_received': 0,
                        'frames_decoded': 0,
                        'active': True,
                        'consecutive_errors': 0
                    }
                    
                    # Register with frame sequencing manager
                    frame_sequencing_manager.register_client(
                        client_id, 
                        lambda frame_data: self._display_sequenced_frame(client_id, frame_data)
                    )
                    
                    logger.info(f"Added sequenced video stream for client {client_id}")
                    
                    # Notify stream status callback
                    if self.stream_status_callback:
                        self.stream_status_callback(client_id, True)
                
                # Update statistics
                stream_info = self.video_streams[client_id]
                stream_info['packets_received'] += 1
                stream_info['last_packet_time'] = time.time()
                self.stats['total_frames_received'] += 1
            
            # Process with frame sequencing for chronological order
            self._process_packet_sequenced(client_id, video_packet)
            
        except Exception as e:
            logger.error(f"Sequenced video packet processing error for {client_id}: {e}")
            self.stats['decode_errors'] += 1
            self._handle_processing_error(client_id)
    
    def _process_packet_sequenced(self, client_id: str, video_packet: UDPPacket):
        """Process packet with enhanced frame sequencing for perfect synchronization."""
        try:
            # Extract timing information from packet with validation
            sequence_number = video_packet.sequence_num
            capture_timestamp = getattr(video_packet, 'capture_timestamp', time.perf_counter())
            network_timestamp = getattr(video_packet, 'network_timestamp', time.perf_counter())
            
            # Validate and correct timestamps for chronological order
            current_time = time.perf_counter()
            
            # Handle future timestamps (clock skew)
            if capture_timestamp > current_time + 1.0:
                capture_timestamp = current_time
                logger.debug(f"Corrected future timestamp for {client_id}")
            
            # Handle duplicate or old timestamps
            if hasattr(self, '_last_capture_timestamps'):
                if client_id not in self._last_capture_timestamps:
                    self._last_capture_timestamps = {}
                
                if client_id in self._last_capture_timestamps:
                    last_timestamp = self._last_capture_timestamps[client_id]
                    if capture_timestamp <= last_timestamp:
                        # Ensure chronological progression
                        capture_timestamp = last_timestamp + 0.001
                        logger.debug(f"Adjusted timestamp for chronological order: {client_id}")
                
                self._last_capture_timestamps[client_id] = capture_timestamp
            
            # Decompress frame with error handling
            frame = self._decompress_frame_stable(video_packet.data)
            
            if frame is not None:
                # Add frame to sequencer for chronological ordering with enhanced sync
                success = frame_sequencing_manager.add_frame(
                    client_id=client_id,
                    sequence_number=sequence_number,
                    capture_timestamp=capture_timestamp,
                    network_timestamp=network_timestamp,
                    frame_data=frame
                )
                
                if success:
                    # Update stream statistics
                    with self._lock:
                        if client_id in self.video_streams:
                            self.video_streams[client_id]['frames_decoded'] += 1
                            self.video_streams[client_id]['consecutive_errors'] = 0
                            
                    logger.debug(f"Added synchronized frame {sequence_number} for {client_id}")
                else:
                    logger.debug(f"Frame {sequence_number} rejected by synchronizer for {client_id}")
            else:
                self._handle_processing_error(client_id)
                
        except Exception as e:
            logger.error(f"Synchronized packet processing error for {client_id}: {e}")
            self._handle_processing_error(client_id)
    def _display_sequenced_frame(self, client_id: str, frame_data: np.ndarray):
        """Display frame that has been sequenced for perfect chronological order."""
        try:
            # Validate frame data
            if frame_data is None or frame_data.size == 0:
                logger.warning(f"Invalid frame data for {client_id}")
                return
            
            # Display frame through callback system with synchronization
            if self.frame_update_callback:
                # Add timestamp for synchronization tracking
                display_timestamp = time.perf_counter()
                
                # Call the callback with synchronized frame
                self.frame_update_callback(client_id, frame_data)
                
                # Update statistics
                with self._lock:
                    self.stats['total_frames_rendered'] += 1
                    
                logger.debug(f"Displayed synchronized frame for {client_id} at {display_timestamp:.6f}")
            
        except Exception as e:
            logger.error(f"Synchronized frame display error for {client_id}: {e}")
    def _process_packet_stable(self, client_id: str, packet_data: bytes):
        """Process packet with stability and error handling."""
        try:
            # Decompress frame with error handling
            frame = self._decompress_frame_stable(packet_data)
            
            if frame is not None:
                # Update stream statistics
                with self._lock:
                    if client_id in self.video_streams:
                        self.video_streams[client_id]['frames_decoded'] += 1
                        self.video_streams[client_id]['consecutive_errors'] = 0
                
                # Display frame with stability callback
                if self.frame_update_callback:
                    try:
                        self.frame_update_callback(client_id, frame)
                    except Exception as e:
                        logger.warning(f"Frame update callback error for {client_id}: {e}")
                        self._handle_processing_error(client_id)
            else:
                self._handle_processing_error(client_id)
                
        except Exception as e:
            logger.error(f"Stable packet processing error for {client_id}: {e}")
            self._handle_processing_error(client_id)
    
    def _decompress_frame_stable(self, compressed_data: bytes) -> Optional[np.ndarray]:
        """Decompress frame with stability and error handling."""
        try:
            if not compressed_data or len(compressed_data) == 0:
                return None
            
            # Convert bytes to numpy array with validation
            nparr = np.frombuffer(compressed_data, np.uint8)
            
            if nparr.size == 0:
                return None
            
            # Decode JPEG image with error handling
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None or frame.size == 0:
                logger.warning("Failed to decode video frame")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame decompression error: {e}")
            return None
    
    def _handle_processing_error(self, client_id: str):
        """Handle processing errors with recovery."""
        try:
            with self._lock:
                if client_id in self.video_streams:
                    stream_info = self.video_streams[client_id]
                    stream_info['consecutive_errors'] = stream_info.get('consecutive_errors', 0) + 1
                    
                    # If too many errors, temporarily disable stream
                    if stream_info['consecutive_errors'] >= 5:
                        logger.warning(f"Too many errors for {client_id}, temporarily disabling")
                        stream_info['active'] = False
                        
                        # Re-enable after delay
                        threading.Timer(2.0, lambda: self._reset_stream_errors(client_id)).start()
                        
        except Exception as e:
            logger.error(f"Error handling processing error for {client_id}: {e}")
    
    def _reset_stream_errors(self, client_id: str):
        """Reset stream error count."""
        try:
            with self._lock:
                if client_id in self.video_streams:
                    self.video_streams[client_id]['consecutive_errors'] = 0
                    self.video_streams[client_id]['active'] = True
                    logger.info(f"Reset errors for {client_id}, stream re-enabled")
        except Exception as e:
            logger.error(f"Error resetting stream errors for {client_id}: {e}")
    
    def _extreme_display_callback(self, client_id: str, frame: np.ndarray):
        """Extreme optimization display callback."""
        try:
            # Immediate frame update callback
            if self.frame_update_callback:
                self.frame_update_callback(client_id, frame)
            
            # Update statistics
            with self._lock:
                if client_id in self.video_streams:
                    self.video_streams[client_id]['frames_decoded'] += 1
                self.stats['total_frames_rendered'] += 1
                
        except Exception as e:
            logger.debug(f"Extreme display callback error: {e}")
    
    def process_video_packet_standard(self, video_packet: UDPPacket):
        """
        Process incoming video packet with standard optimization and buffering.
        
        Args:
            video_packet: UDP packet containing compressed video data
        """
        if not self.is_rendering:
            return
        
        try:
            client_id = video_packet.sender_id
            packet_timestamp = time.time()
            
            # Register transmission timing
            video_optimizer.sync_manager.register_frame_timing(
                client_id, 'transmit', packet_timestamp, video_packet.sequence_num
            )
            
            # Initialize stream if new
            with self._lock:
                if client_id not in self.video_streams:
                    self.video_streams[client_id] = {
                        'last_packet_time': packet_timestamp,
                        'packets_received': 0,
                        'frames_decoded': 0,
                        'last_sequence': -1,
                        'active': True,
                        'packet_loss_count': 0,
                        'expected_sequence': 0
                    }
                    self.frame_buffers[client_id] = deque(maxlen=self.max_buffer_size)
                    
                    # Register client with optimizer
                    video_optimizer.register_client(client_id)
                    
                    logger.info(f"Added optimized video stream for client {client_id}")
                    
                    # Notify stream status callback
                    if self.stream_status_callback:
                        self.stream_status_callback(client_id, True)
                
                stream_info = self.video_streams[client_id]
                
                # Detect packet loss
                expected_seq = stream_info['expected_sequence']
                if video_packet.sequence_num > expected_seq:
                    lost_packets = video_packet.sequence_num - expected_seq
                    stream_info['packet_loss_count'] += lost_packets
                    logger.debug(f"Detected {lost_packets} lost packets for {client_id}")
                
                stream_info['expected_sequence'] = video_packet.sequence_num + 1
                
                # Update stream statistics
                stream_info['last_packet_time'] = packet_timestamp
                stream_info['packets_received'] += 1
                stream_info['last_sequence'] = video_packet.sequence_num
                stream_info['active'] = True
                
                self.stats['total_frames_received'] += 1
                self.stats['active_video_streams'] = len(self.video_streams)
                
                # Calculate packet loss rate
                if stream_info['packets_received'] > 0:
                    packet_loss_rate = stream_info['packet_loss_count'] / stream_info['packets_received']
                    
                    # Update network conditions in optimizer
                    video_optimizer.update_network_conditions(
                        packet_loss_rate, 
                        0.02,  # Placeholder latency - would need actual measurement
                        len(video_packet.data)  # Throughput approximation
                    )
            
            # Decompress video frame
            decode_start_time = time.time()
            frame = self._decompress_frame(video_packet.data)
            
            if frame is not None:
                # Register decode timing
                video_optimizer.sync_manager.register_frame_timing(
                    client_id, 'decode', time.time(), video_packet.sequence_num
                )
                
                # Add frame to optimizer buffer instead of simple deque
                video_optimizer.add_frame(
                    client_id, 
                    frame, 
                    packet_timestamp, 
                    video_packet.sequence_num
                )
                
                with self._lock:
                    stream_info['frames_decoded'] += 1
                
                # Ultra-fast mode: immediate display without buffering for LAN
                if self.frame_update_callback:
                    # Direct callback with original frame for zero-latency display
                    self.frame_update_callback(client_id, frame)
                
                # Also add to optimizer buffer for statistics (but don't wait for it)
                try:
                    optimized_frame = video_optimizer.get_frame(client_id)
                except:
                    pass  # Ignore optimizer delays
            
        except Exception as e:
            logger.error(f"Error processing video packet: {e}")
            self.stats['decode_errors'] += 1
    
    def _decompress_frame(self, compressed_data: bytes) -> Optional[np.ndarray]:
        """
        Decompress video frame from JPEG data.
        
        Args:
            compressed_data: Compressed video frame data
            
        Returns:
            np.ndarray: Decompressed video frame or None if decompression failed
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(compressed_data, np.uint8)
            
            # Decode JPEG image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("Failed to decode video frame")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Error decompressing frame: {e}")
            return None
    
    def _render_loop(self):
        """Main rendering loop for processing video frames."""
        logger.info("Video render loop started")
        
        while self.is_rendering:
            try:
                # Process frames from all active streams
                self._process_frame_buffers()
                
                # Clean up inactive streams
                self._cleanup_inactive_streams()
                
                # Ultra-fast rendering with minimal delay
                time.sleep(1.0 / 120)  # 120 FPS for ultra-smooth, immediate playback
                
            except Exception as e:
                if self.is_rendering:
                    logger.error(f"Error in video render loop: {e}")
                break
        
        logger.info("Video render loop ended")
    
    def _process_frame_buffers(self):
        """Process frames from all client buffers."""
        with self._lock:
            for client_id, frame_buffer in self.frame_buffers.items():
                if frame_buffer:
                    # Get the most recent frame
                    frame_data = frame_buffer.popleft()
                    frame = frame_data['frame']
                    
                    # Update statistics
                    self.stats['total_frames_rendered'] += 1
                    
                    # Call frame update callback
                    if self.frame_update_callback:
                        try:
                            self.frame_update_callback(client_id, frame)
                        except Exception as e:
                            logger.warning(f"Error in frame update callback: {e}")
    
    def _cleanup_inactive_streams(self, timeout_seconds: float = 10.0):
        """
        Clean up video streams that haven't received packets recently.
        
        Args:
            timeout_seconds: Timeout in seconds for inactive streams
        """
        current_time = time.time()
        inactive_clients = []
        
        with self._lock:
            for client_id, stream_info in self.video_streams.items():
                if current_time - stream_info['last_packet_time'] > timeout_seconds:
                    if stream_info['active']:
                        stream_info['active'] = False
                        inactive_clients.append(client_id)
            
            # Remove inactive streams
            for client_id in inactive_clients:
                logger.info(f"Removing inactive video stream: {client_id}")
                
                # Notify stream status callback
                if self.stream_status_callback:
                    self.stream_status_callback(client_id, False)
                
                # Clean up resources
                if client_id in self.frame_buffers:
                    del self.frame_buffers[client_id]
                
                if client_id in self.video_streams:
                    del self.video_streams[client_id]
            
            self.stats['active_video_streams'] = len(self.video_streams)
    
    def remove_video_stream(self, client_id: str):
        """
        Remove video stream for a specific client.
        
        Args:
            client_id: ID of the client to remove
        """
        with self._lock:
            if client_id in self.video_streams:
                logger.info(f"Removing sequenced video stream for client {client_id}")
                
                # Unregister from all systems
                video_optimizer.unregister_client(client_id)
                extreme_video_optimizer.unregister_client(client_id)
                frame_sequencing_manager.unregister_client(client_id)
                
                # Notify stream status callback
                if self.stream_status_callback:
                    self.stream_status_callback(client_id, False)
                
                # Clean up resources
                if client_id in self.frame_buffers:
                    del self.frame_buffers[client_id]
                
                del self.video_streams[client_id]
                self.stats['active_video_streams'] = len(self.video_streams)
    
    def get_active_streams(self) -> list:
        """
        Get list of active video stream client IDs.
        
        Returns:
            list: List of client IDs with active video streams
        """
        with self._lock:
            return [client_id for client_id, stream_info in self.video_streams.items() 
                   if stream_info.get('active', False)]
    
    def get_latest_frame(self, client_id: str) -> Optional[np.ndarray]:
        """
        Get the latest frame for a specific client.
        
        Args:
            client_id: ID of the client
            
        Returns:
            np.ndarray: Latest video frame or None if not available
        """
        with self._lock:
            if client_id in self.frame_buffers and self.frame_buffers[client_id]:
                # Return the most recent frame without removing it
                return self.frame_buffers[client_id][-1]['frame']
            return None
    
    def get_render_stats(self) -> dict:
        """
        Get video rendering statistics.
        
        Returns:
            dict: Rendering statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_rendering'] = self.is_rendering
            stats['active_streams'] = {}
            
            # Add per-client statistics
            for client_id, stream_info in self.video_streams.items():
                stats['active_streams'][client_id] = {
                    'packets_received': stream_info['packets_received'],
                    'frames_decoded': stream_info['frames_decoded'],
                    'last_packet_time': stream_info['last_packet_time'],
                    'active': stream_info['active']
                }
            
            if stats['render_start_time']:
                stats['render_duration'] = time.time() - stats['render_start_time']
                
                # Calculate rendering FPS
                if stats['render_duration'] > 0:
                    stats['average_render_fps'] = stats['total_frames_rendered'] / stats['render_duration']
            
            return stats


class VideoManager:
    """
    High-level video management for the collaboration client.
    
    Coordinates video capture and rendering components.
    """
    
    def __init__(self, client_id: str, connection_manager=None):
        """
        Initialize the video manager.
        
        Args:
            client_id: Unique identifier for this client
            connection_manager: Connection manager for network communication
        """
        self.client_id = client_id
        self.connection_manager = connection_manager
        
        # Video components
        self.video_renderer = VideoRenderer()
        
        # Video manager state
        self.is_active = False
        self._lock = threading.RLock()
        
        # Setup callbacks
        self.video_renderer.set_frame_update_callback(self._on_frame_update)
        self.video_renderer.set_stream_status_callback(self._on_stream_status_change)
        
        # GUI callbacks
        self.gui_frame_callback: Optional[Callable[[str, np.ndarray], None]] = None
        self.gui_status_callback: Optional[Callable[[str, bool], None]] = None
    
    def set_gui_callbacks(self, frame_callback: Callable[[str, np.ndarray], None],
                         status_callback: Callable[[str, bool], None]):
        """
        Set GUI callbacks for video updates.
        
        Args:
            frame_callback: Function to call with (client_id, frame) for GUI updates
            status_callback: Function to call with (client_id, active) for status updates
        """
        self.gui_frame_callback = frame_callback
        self.gui_status_callback = status_callback
    
    def start_video_system(self) -> bool:
        """
        Start the optimized video management system.
        
        Returns:
            bool: True if started successfully
        """
        if self.is_active:
            logger.warning("Video system already active")
            return True
        
        try:
            # Start video optimizer
            video_optimizer.start_optimization()
            
            # Start video renderer
            if not self.video_renderer.start_rendering():
                logger.error("Failed to start video renderer")
                video_optimizer.stop_optimization()
                return False
            
            self.is_active = True
            logger.info("Optimized video system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video system: {e}")
            return False
    
    def stop_video_system(self):
        """Stop the optimized video management system."""
        if not self.is_active:
            return
        
        self.is_active = False
        
        # Stop video renderer
        self.video_renderer.stop_rendering()
        
        # Stop video optimizer
        video_optimizer.stop_optimization()
        
        logger.info("Optimized video system stopped")
    
    def process_incoming_video(self, video_packet: UDPPacket):
        """
        Process incoming video packet.
        
        Args:
            video_packet: UDP packet containing video data
        """
        if self.is_active:
            self.video_renderer.process_video_packet(video_packet)
    
    def remove_client_video(self, client_id: str):
        """
        Remove video stream for a disconnected client.
        
        Args:
            client_id: ID of the client to remove
        """
        self.video_renderer.remove_video_stream(client_id)
    
    def _on_frame_update(self, client_id: str, frame: np.ndarray):
        """Handle frame updates from video renderer."""
        try:
            if self.gui_frame_callback:
                self.gui_frame_callback(client_id, frame)
        except Exception as e:
            logger.error(f"Error in GUI frame callback: {e}")
    
    def _on_stream_status_change(self, client_id: str, active: bool):
        """Handle stream status changes from video renderer."""
        try:
            if self.gui_status_callback:
                self.gui_status_callback(client_id, active)
        except Exception as e:
            logger.error(f"Error in GUI status callback: {e}")
    
    def get_video_stats(self) -> dict:
        """
        Get comprehensive video statistics.
        
        Returns:
            dict: Video system statistics
        """
        stats = {
            'is_active': self.is_active,
            'client_id': self.client_id,
            'renderer_stats': self.video_renderer.get_render_stats()
        }
        
        return stats