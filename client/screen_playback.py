"""
Screen playback module for the collaboration client.
Handles screen frame reception and display for screen sharing.
"""

import cv2
import threading
import time
import logging
import numpy as np
from typing import Optional, Callable
from common.messages import TCPMessage, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenPlayback:
    """
    Screen playback component for displaying shared screens.
    
    Handles:
    - Screen frame reception and decompression
    - Screen frame display in dedicated area
    - Screen sharing session management
    """
    
    def __init__(self, client_id: str):
        """
        Initialize the screen playback system.
        
        Args:
            client_id: Unique identifier for this client
        """
        self.client_id = client_id
        
        # Screen playback state
        self.is_receiving = False
        self.current_presenter_id: Optional[str] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_frame_time: Optional[float] = None
        
        # Frame processing
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_displayed': 0,
            'playback_errors': 0,
            'playback_start_time': None,
            'last_frame_time': None,
            'total_bytes_received': 0,
            'average_frame_size': 0
        }
        
        # Callbacks
        self.frame_callback: Optional[Callable[[np.ndarray, str], None]] = None
        self.presenter_change_callback: Optional[Callable[[str], None]] = None
    
    def set_frame_callback(self, callback: Callable[[np.ndarray, str], None]):
        """
        Set callback function to receive screen frames for display.
        
        Args:
            callback: Function to call with screen frame data and presenter ID
        """
        self.frame_callback = callback
    
    def set_presenter_change_callback(self, callback: Callable[[str], None]):
        """
        Set callback function to be notified of presenter changes.
        
        Args:
            callback: Function to call when presenter changes
        """
        self.presenter_change_callback = callback
    
    def start_receiving(self) -> bool:
        """
        Start receiving screen frames.
        
        Returns:
            bool: True if receiving started successfully
        """
        if self.is_receiving:
            logger.warning("Screen playback already receiving")
            return True
        
        try:
            self.is_receiving = True
            self.stats['playback_start_time'] = time.time()
            
            logger.info("Screen playback started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start screen playback: {e}")
            return False
    
    def stop_receiving(self):
        """Stop receiving screen frames."""
        if not self.is_receiving:
            return
        
        logger.info("Stopping screen playback...")
        self.is_receiving = False
        
        # Clear current state
        with self._lock:
            self.current_presenter_id = None
            self.last_frame = None
            self.last_frame_time = None
        
        logger.info("Screen playback stopped")
    
    def process_screen_message(self, screen_message: TCPMessage) -> bool:
        """
        Process incoming screen frame message.
        
        Args:
            screen_message: TCP message containing screen frame data
            
        Returns:
            bool: True if frame was processed successfully
        """
        if not self.is_receiving:
            return False
        
        try:
            # Verify message type
            if screen_message.msg_type != MessageType.SCREEN_SHARE.value:
                logger.warning(f"Unexpected message type for screen frame: {screen_message.msg_type}")
                return False
            
            # Extract frame data
            if 'frame_data' not in screen_message.data:
                logger.warning("Screen message missing frame data")
                return False
            
            presenter_id = screen_message.sender_id
            frame_data_hex = screen_message.data['frame_data']
            
            # Update presenter if changed
            if self.current_presenter_id != presenter_id:
                self._update_presenter(presenter_id)
            
            # Decompress and display frame
            frame = self._decompress_frame(frame_data_hex)
            if frame is not None:
                self._display_frame(frame, presenter_id)
                return True
            else:
                self.stats['playback_errors'] += 1
                return False
            
        except Exception as e:
            logger.error(f"Error processing screen message: {e}")
            self.stats['playback_errors'] += 1
            return False
    
    def _update_presenter(self, presenter_id: str):
        """
        Update the current presenter.
        
        Args:
            presenter_id: ID of the new presenter
        """
        with self._lock:
            old_presenter = self.current_presenter_id
            self.current_presenter_id = presenter_id
            
            logger.info(f"Presenter changed from {old_presenter} to {presenter_id}")
            
            # Notify callback of presenter change
            if self.presenter_change_callback:
                try:
                    self.presenter_change_callback(presenter_id)
                except Exception as e:
                    logger.warning(f"Error in presenter change callback: {e}")
    
    def _decompress_frame(self, frame_data_hex: str) -> Optional[np.ndarray]:
        """
        Decompress screen frame from hex string.
        
        Args:
            frame_data_hex: Hex string containing compressed frame data
            
        Returns:
            np.ndarray: Decompressed frame or None if decompression failed
        """
        try:
            # Convert hex string to bytes
            frame_bytes = bytes.fromhex(frame_data_hex)
            
            # Update statistics
            frame_size = len(frame_bytes)
            self.stats['total_bytes_received'] += frame_size
            
            # Calculate running average frame size
            frames_received = self.stats['frames_received']
            if frames_received > 0:
                self.stats['average_frame_size'] = (
                    (self.stats['average_frame_size'] * frames_received + frame_size) / 
                    (frames_received + 1)
                )
            else:
                self.stats['average_frame_size'] = frame_size
            
            # Decode JPEG frame
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                self.stats['frames_received'] += 1
                return frame
            else:
                logger.warning("Failed to decode screen frame")
                return None
                
        except Exception as e:
            logger.error(f"Error decompressing screen frame: {e}")
            return None
    
    def _display_frame(self, frame: np.ndarray, presenter_id: str):
        """
        Display screen frame via callback.
        
        Args:
            frame: Decompressed screen frame
            presenter_id: ID of the presenter
        """
        try:
            with self._lock:
                self.last_frame = frame.copy()
                self.last_frame_time = time.time()
                self.stats['last_frame_time'] = self.last_frame_time
            
            # Call frame callback for display
            if self.frame_callback:
                try:
                    self.frame_callback(frame, presenter_id)
                    self.stats['frames_displayed'] += 1
                except Exception as e:
                    logger.warning(f"Error in frame callback: {e}")
            
        except Exception as e:
            logger.error(f"Error displaying screen frame: {e}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the current screen frame.
        
        Returns:
            np.ndarray: Current frame or None if no frame available
        """
        with self._lock:
            return self.last_frame.copy() if self.last_frame is not None else None
    
    def get_current_presenter(self) -> Optional[str]:
        """
        Get the current presenter ID.
        
        Returns:
            str: Current presenter ID or None if no presenter
        """
        with self._lock:
            return self.current_presenter_id
    
    def is_screen_sharing_active(self) -> bool:
        """
        Check if screen sharing is currently active.
        
        Returns:
            bool: True if screen sharing is active
        """
        with self._lock:
            if not self.is_receiving or not self.last_frame_time:
                return False
            
            # Consider screen sharing active if we received a frame in the last 10 seconds
            return time.time() - self.last_frame_time < 10.0
    
    def get_playback_stats(self) -> dict:
        """
        Get screen playback statistics.
        
        Returns:
            dict: Playback statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_receiving'] = self.is_receiving
            stats['current_presenter_id'] = self.current_presenter_id
            stats['is_screen_sharing_active'] = self.is_screen_sharing_active()
            
            if stats['playback_start_time']:
                stats['playback_duration'] = time.time() - stats['playback_start_time']
                
                # Calculate actual FPS
                if stats['playback_duration'] > 0:
                    stats['actual_fps'] = stats['frames_received'] / stats['playback_duration']
            
            return stats
    
    def handle_presenter_start(self, presenter_id: str):
        """
        Handle presenter starting screen sharing.
        
        Args:
            presenter_id: ID of the presenter starting screen sharing
        """
        logger.info(f"Presenter {presenter_id} started screen sharing")
        self._update_presenter(presenter_id)
    
    def handle_presenter_stop(self, presenter_id: str):
        """
        Handle presenter stopping screen sharing.
        
        Args:
            presenter_id: ID of the presenter stopping screen sharing
        """
        logger.info(f"Presenter {presenter_id} stopped screen sharing")
        
        with self._lock:
            if self.current_presenter_id == presenter_id:
                self.current_presenter_id = None
                self.last_frame = None
                self.last_frame_time = None
                
                # Notify callback of presenter change
                if self.presenter_change_callback:
                    try:
                        self.presenter_change_callback(None)
                    except Exception as e:
                        logger.warning(f"Error in presenter change callback: {e}")