"""
Video capture and compression module for the collaboration client.
Handles webcam video capture using OpenCV and real-time compression.
"""

import threading
import time
import logging
from typing import Optional, Callable, Tuple
import numpy as np
from common.messages import UDPPacket, MessageFactory
from common.platform_utils import PLATFORM_INFO, DeviceUtils, ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Platform-specific imports
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available - video capture disabled")


class VideoCapture:
    """
    Video capture component for webcam video streaming.
    
    Handles:
    - Webcam video capture using OpenCV
    - Real-time video compression with lightweight codec
    - Video frame transmission via UDP packets
    """
    
    # Video configuration constants - optimized for 60 FPS low latency
    DEFAULT_WIDTH = 240  # Reduced resolution for smaller packets
    DEFAULT_HEIGHT = 180  # Reduced resolution for smaller packets
    DEFAULT_FPS = 60  # 60 FPS for ultra-smooth video
    COMPRESSION_QUALITY = 40  # Lower quality for smaller packet size
    
    def __init__(self, client_id: str, connection_manager=None):
        """
        Initialize the video capture system.
        
        Args:
            client_id: Unique identifier for this client
            connection_manager: Connection manager for sending video packets
        """
        self.client_id = client_id
        self.connection_manager = connection_manager
        
        # Video capture state
        self.camera: Optional[cv2.VideoCapture] = None
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        
        # Video settings
        self.width = self.DEFAULT_WIDTH
        self.height = self.DEFAULT_HEIGHT
        self.fps = self.DEFAULT_FPS
        self.compression_quality = self.COMPRESSION_QUALITY
        
        # Frame sequence tracking
        self.sequence_number = 0
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'frames_captured': 0,
            'frames_sent': 0,
            'capture_errors': 0,
            'capture_start_time': None,
            'last_frame_time': None,
            'average_frame_size': 0,
            'total_bytes_sent': 0
        }
        
        # Callbacks
        self.frame_callback: Optional[Callable[[np.ndarray], None]] = None
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Set callback function to receive captured frames for local display.
        
        Args:
            callback: Function to call with captured frame data
        """
        self.frame_callback = callback
    
    def set_video_settings(self, width: int = None, height: int = None, 
                          fps: int = None, quality: int = None):
        """
        Update video capture settings.
        
        Args:
            width: Video width in pixels
            height: Video height in pixels
            fps: Frames per second
            quality: JPEG compression quality (0-100)
        """
        with self._lock:
            if width is not None:
                self.width = max(160, min(1920, width))  # Clamp to reasonable range
            if height is not None:
                self.height = max(120, min(1080, height))
            if fps is not None:
                self.fps = max(5, min(30, fps))  # Clamp to reasonable range
            if quality is not None:
                self.compression_quality = max(10, min(100, quality))
        
        logger.info(f"Video settings updated: {self.width}x{self.height} @ {self.fps}fps, quality={self.compression_quality}")
    
    def start_capture(self, camera_index: int = 0) -> bool:
        """
        Start video capture from webcam.
        
        Args:
            camera_index: Camera device index (0 for default camera)
            
        Returns:
            bool: True if capture started successfully
        """
        if not OPENCV_AVAILABLE:
            logger.error("OpenCV not available - video capture disabled")
            return False
        
        if not PLATFORM_INFO.get_capability('video_capture'):
            logger.error("Video capture not supported on this platform")
            return False
        
        if self.is_capturing:
            logger.warning("Video capture already running")
            return True
        
        try:
            # Get available video devices
            available_devices = DeviceUtils.get_video_devices()
            if not available_devices:
                logger.error("No video devices found")
                return False
            
            # Use specified camera index or first available
            if camera_index >= len(available_devices):
                logger.warning(f"Camera index {camera_index} not available, using camera 0")
                camera_index = 0
            
            logger.info(f"Attempting to open camera {camera_index}")
            
            # Initialize camera
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                error_msg = f"Failed to open camera {camera_index}"
                logger.error(error_msg)
                
                # Try alternative camera indices
                for alt_index in range(3):
                    if alt_index != camera_index:
                        logger.info(f"Trying alternative camera {alt_index}")
                        self.camera = cv2.VideoCapture(alt_index)
                        if self.camera.isOpened():
                            logger.info(f"Successfully opened camera {alt_index}")
                            camera_index = alt_index
                            break
                        self.camera.release()
                
                if not self.camera.isOpened():
                    return False
            
            # Configure camera settings for low latency
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Ultra-low latency optimizations for 60 FPS
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Use MJPEG for better performance
            
            # Additional 60 FPS optimizations
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Disable auto exposure for consistent timing
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus for consistent timing
            
            # Verify actual settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Start capture thread
            self.is_capturing = True
            self.stats['capture_start_time'] = time.time()
            self.sequence_number = 0
            
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()
            
            logger.info("Video capture started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video capture: {e}")
            self._cleanup_camera()
            return False
    
    def stop_capture(self):
        """Stop video capture."""
        if not self.is_capturing:
            return
        
        logger.info("Stopping video capture...")
        self.is_capturing = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        # Cleanup camera
        self._cleanup_camera()
        
        logger.info("Video capture stopped")
    
    def _cleanup_camera(self):
        """Clean up camera resources."""
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")
            finally:
                self.camera = None
    
    def _capture_loop(self):
        """Main video capture loop running in separate thread."""
        logger.info("Video capture loop started")
        
        frame_interval = 1.0 / self.fps  # Time between frames
        last_frame_time = 0
        
        while self.is_capturing and self.camera:
            try:
                current_time = time.time()
                
                # For 60 FPS, capture as fast as possible with zero delay
                if self.fps >= 60 and current_time - last_frame_time < frame_interval:
                    continue  # No sleep for 60+ FPS to minimize latency
                elif self.fps >= 30 and current_time - last_frame_time < frame_interval:
                    continue  # No sleep for 30+ FPS either
                elif current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)  # Tiny sleep only for very low FPS
                    continue
                
                # Capture frame
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    logger.warning("Failed to capture frame")
                    self.stats['capture_errors'] += 1
                    time.sleep(0.1)  # Wait before retrying
                    continue
                
                # Process and send frame
                self._process_frame(frame)
                
                last_frame_time = current_time
                self.stats['frames_captured'] += 1
                self.stats['last_frame_time'] = current_time
                
            except Exception as e:
                if self.is_capturing:  # Only log if we're still supposed to be capturing
                    logger.error(f"Error in video capture loop: {e}")
                    self.stats['capture_errors'] += 1
                break
        
        logger.info("Video capture loop ended")
    
    def _process_frame(self, frame: np.ndarray):
        """
        Process captured frame: resize, compress, and transmit.
        
        Args:
            frame: Captured video frame from OpenCV
        """
        try:
            # Resize frame if needed
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            
            # Call frame callback for local display
            if self.frame_callback:
                try:
                    self.frame_callback(frame.copy())
                except Exception as e:
                    logger.warning(f"Error in frame callback: {e}")
            
            # Compress frame using JPEG
            compressed_frame = self._compress_frame(frame)
            
            if compressed_frame is not None:
                # Send compressed frame via UDP
                self._send_video_packet(compressed_frame)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            self.stats['capture_errors'] += 1
    
    def _compress_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Compress video frame using JPEG compression.
        
        Args:
            frame: Video frame to compress
            
        Returns:
            bytes: Compressed frame data or None if compression failed
        """
        try:
            # JPEG compression parameters
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, self.compression_quality,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1
            ]
            
            # Encode frame as JPEG
            success, encoded_frame = cv2.imencode('.jpg', frame, encode_params)
            
            if success:
                compressed_data = encoded_frame.tobytes()
                
                # Update statistics
                frame_size = len(compressed_data)
                self.stats['total_bytes_sent'] += frame_size
                
                # Calculate running average frame size
                frames_sent = self.stats['frames_sent']
                if frames_sent > 0:
                    self.stats['average_frame_size'] = (
                        (self.stats['average_frame_size'] * frames_sent + frame_size) / 
                        (frames_sent + 1)
                    )
                else:
                    self.stats['average_frame_size'] = frame_size
                
                return compressed_data
            else:
                logger.warning("Failed to encode frame as JPEG")
                return None
                
        except Exception as e:
            logger.error(f"Error compressing frame: {e}")
            return None
    
    def _send_video_packet(self, compressed_frame: bytes):
        """
        Send compressed video frame as UDP packet.
        
        Args:
            compressed_frame: Compressed video frame data
        """
        try:
            if not self.connection_manager:
                return
            
            # Check packet size limit (increased for better quality on LAN)
            max_packet_size = 32768  # 32KB maximum for LAN networks
            if len(compressed_frame) > max_packet_size:
                logger.warning(f"Video frame too large ({len(compressed_frame)} bytes), skipping")
                return
            
            # Create video UDP packet
            with self._lock:
                video_packet = MessageFactory.create_video_packet(
                    sender_id=self.client_id,
                    sequence_num=self.sequence_number,
                    video_data=compressed_frame
                )
                self.sequence_number += 1
            
            # Send packet via connection manager
            success = self.connection_manager.send_udp_packet(video_packet)
            
            if success:
                self.stats['frames_sent'] += 1
            else:
                # Reduce warning spam - only log occasionally
                if self.stats['frames_captured'] % 100 == 0:
                    logger.warning("Video packets not being sent (UDP connection issue)")
                
        except Exception as e:
            logger.error(f"Error sending video packet: {e}")
    
    def get_capture_stats(self) -> dict:
        """
        Get video capture statistics.
        
        Returns:
            dict: Capture statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_capturing'] = self.is_capturing
            stats['current_settings'] = {
                'width': self.width,
                'height': self.height,
                'fps': self.fps,
                'compression_quality': self.compression_quality
            }
            
            if stats['capture_start_time']:
                stats['capture_duration'] = time.time() - stats['capture_start_time']
                
                # Calculate actual FPS
                if stats['capture_duration'] > 0:
                    stats['actual_fps'] = stats['frames_captured'] / stats['capture_duration']
            
            return stats
    
    def is_camera_available(self, camera_index: int = 0) -> bool:
        """
        Check if camera is available for capture.
        
        Args:
            camera_index: Camera device index to check
            
        Returns:
            bool: True if camera is available
        """
        if not OPENCV_AVAILABLE:
            return False
        
        try:
            test_camera = cv2.VideoCapture(camera_index)
            is_available = test_camera.isOpened()
            test_camera.release()
            return is_available
        except Exception as e:
            logger.debug(f"Camera {camera_index} not available: {e}")
            return False
    
    def get_available_cameras(self) -> list:
        """
        Get list of available camera indices with device information.
        
        Returns:
            list: List of available camera information dictionaries
        """
        if not OPENCV_AVAILABLE:
            return []
        
        # Use platform utils to get detailed device information
        return DeviceUtils.get_video_devices()