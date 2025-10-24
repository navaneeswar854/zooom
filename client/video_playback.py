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
        Process incoming video packet from server.
        
        Args:
            video_packet: UDP packet containing compressed video data
        """
        if not self.is_rendering:
            return
        
        try:
            client_id = video_packet.sender_id
            
            # Initialize stream if new
            with self._lock:
                if client_id not in self.video_streams:
                    self.video_streams[client_id] = {
                        'last_packet_time': time.time(),
                        'packets_received': 0,
                        'frames_decoded': 0,
                        'last_sequence': -1,
                        'active': True
                    }
                    self.frame_buffers[client_id] = deque(maxlen=self.max_buffer_size)
                    
                    logger.info(f"Added video stream for client {client_id}")
                    
                    # Notify stream status callback
                    if self.stream_status_callback:
                        self.stream_status_callback(client_id, True)
                
                stream_info = self.video_streams[client_id]
                
                # Update stream statistics
                stream_info['last_packet_time'] = time.time()
                stream_info['packets_received'] += 1
                stream_info['last_sequence'] = video_packet.sequence_num
                stream_info['active'] = True
                
                self.stats['total_frames_received'] += 1
                self.stats['active_video_streams'] = len(self.video_streams)
            
            # Decompress video frame
            frame = self._decompress_frame(video_packet.data)
            
            if frame is not None:
                with self._lock:
                    # Add frame to buffer
                    self.frame_buffers[client_id].append({
                        'frame': frame,
                        'timestamp': time.time(),
                        'sequence': video_packet.sequence_num
                    })
                    
                    stream_info['frames_decoded'] += 1
                
                # Notify frame update callback
                if self.frame_update_callback:
                    self.frame_update_callback(client_id, frame)
            
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
                
                # Sleep to maintain 60 FPS rendering
                time.sleep(1.0 / 60)  # 60 FPS for ultra-smooth playback
                
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
                logger.info(f"Removing video stream for client {client_id}")
                
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
        Start the video management system.
        
        Returns:
            bool: True if started successfully
        """
        if self.is_active:
            logger.warning("Video system already active")
            return True
        
        try:
            # Start video renderer
            if not self.video_renderer.start_rendering():
                logger.error("Failed to start video renderer")
                return False
            
            self.is_active = True
            logger.info("Video system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video system: {e}")
            return False
    
    def stop_video_system(self):
        """Stop the video management system."""
        if not self.is_active:
            return
        
        self.is_active = False
        
        # Stop video renderer
        self.video_renderer.stop_rendering()
        
        logger.info("Video system stopped")
    
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