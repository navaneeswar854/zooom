"""
Video capture and compression module for the collaboration client.
Handles webcam video capture using OpenCV and real-time compression.
"""

import threading
import time
import logging
from typing import Optional, Callable, Tuple
from collections import deque
import numpy as np
from common.messages import UDPPacket, MessageFactory
from common.platform_utils import PLATFORM_INFO, DeviceUtils, ErrorHandler
from client.video_optimization import video_optimizer
from client.extreme_video_optimizer import extreme_video_optimizer
from client.stable_video_system import stability_manager

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
    
    # Video configuration constants - optimized for ultra-fast transfer and low latency
    DEFAULT_WIDTH = 320  # Standard resolution for compatibility
    DEFAULT_HEIGHT = 240  # Standard resolution for compatibility
    DEFAULT_FPS = 30  # 30 FPS for smooth video (most cameras support this)
    COMPRESSION_QUALITY = 60  # Higher quality for better visual experience
    
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
        
        # Frame sequence tracking with high-precision timestamps
        self.sequence_number = 0
        self._lock = threading.RLock()
        
        # Timestamp synchronization
        self.capture_start_timestamp = None
        self.frame_timestamps = deque(maxlen=100)  # Track frame timing
        
        # Statistics
        self.stats = {
            'frames_captured': 0,
            'frames_sent': 0,
            'capture_errors': 0,
            'capture_start_time': None,
            'last_frame_time': None,
            'average_frame_size': 0,
            'total_bytes_sent': 0,
            'frames_dropped': 0,
            'encoding_times': []
        }
        
        # Optimization integration
        self.adaptive_settings = {
            'quality': self.compression_quality,
            'fps': self.fps,
            'resolution_scale': 1.0
        }
        self.last_quality_update = 0
        
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
            
            # Configure camera settings for low latency with fallbacks
            # Try to set desired resolution, but camera may not support it
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # If camera doesn't support our resolution, try common fallbacks
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width != self.width or actual_height != self.height:
                logger.info(f"Camera doesn't support {self.width}x{self.height}, trying fallbacks...")
                
                # Try common small resolutions
                fallback_resolutions = [(320, 240), (160, 120), (176, 144)]
                for fw, fh in fallback_resolutions:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, fw)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, fh)
                    test_w = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                    test_h = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    if test_w == fw and test_h == fh:
                        logger.info(f"Using fallback resolution: {fw}x{fh}")
                        break
            
            # Ultra-low latency optimizations for 60 FPS
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))  # Use MJPEG for better performance
            
            # Additional 30 FPS optimizations
            try:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Disable auto exposure for consistent timing
            except:
                pass  # Some cameras don't support this
            try:
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus for consistent timing
            except:
                pass  # Some cameras don't support this
            
            # Verify actual settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Start capture thread with precise timing
            self.is_capturing = True
            self.stats['capture_start_time'] = time.time()
            self.capture_start_timestamp = time.perf_counter()  # High precision timestamp
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
    
    def _update_adaptive_settings(self):
        """Update adaptive settings based on optimizer recommendations."""
        current_time = time.time()
        
        # Update settings every 2 seconds
        if current_time - self.last_quality_update >= 2.0:
            self.last_quality_update = current_time
            
            # Get optimized settings
            quality_settings = video_optimizer.get_quality_settings()
            
            # Update adaptive settings
            self.adaptive_settings.update(quality_settings)
            
            # Log quality changes
            if abs(self.adaptive_settings['quality'] - self.compression_quality) > 5:
                logger.info(f"Adaptive quality changed to {self.adaptive_settings['quality']}")
    
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
        """Main video capture loop with stability optimization."""
        logger.info("Video capture loop started with stability optimization")
        
        # Enable stability system
        stability_manager.enable_stability()
        
        # Stable capture with error handling
        frame_interval = 1.0 / 25  # 25 FPS for stability
        last_frame_time = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_capturing and self.camera:
            try:
                current_time = time.time()
                
                # Stable frame timing
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)  # Small delay for stability
                    continue
                
                # Capture frame with error handling
                ret, frame = self.camera.read()
                
                if not ret or frame is None:
                    consecutive_errors += 1
                    self.stats['capture_errors'] += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.warning("Too many consecutive capture errors, pausing briefly")
                        time.sleep(0.5)  # Recovery pause
                        consecutive_errors = 0
                    
                    continue
                
                # Reset error count on success
                consecutive_errors = 0
                
                # Process frame with stability
                self._process_frame_stable(frame)
                
                self.stats['frames_captured'] += 1
                self.stats['last_frame_time'] = current_time
                last_frame_time = current_time
                
            except Exception as e:
                if self.is_capturing:
                    logger.error(f"Error in stable capture loop: {e}")
                    self.stats['capture_errors'] += 1
                    consecutive_errors += 1
                    
                    # Recovery delay on errors
                    time.sleep(0.1)
        
        logger.info("Stable video capture loop ended")
    
    def _process_frame_stable(self, frame: np.ndarray):
        """
        Process captured frame with stability optimization and precise timestamping.
        
        Args:
            frame: Captured video frame from OpenCV
        """
        try:
            # Capture precise timestamp for frame sequencing with high precision
            capture_timestamp = time.perf_counter()
            relative_timestamp = capture_timestamp - self.capture_start_timestamp if self.capture_start_timestamp else 0
            
            # Store timestamp for sequencing with chronological validation
            self.frame_timestamps.append(capture_timestamp)
            
            # Validate frame timing for chronological order
            if len(self.frame_timestamps) > 1:
                prev_timestamp = self.frame_timestamps[-2]
                if capture_timestamp <= prev_timestamp:
                    # Adjust timestamp to maintain chronological order
                    capture_timestamp = prev_timestamp + 0.001  # 1ms increment
                    logger.debug(f"Adjusted timestamp to maintain chronological order")
            
            # Stable frame processing with error handling
            
            # Resize frame if needed
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            
            # Local display callback with error handling
            if self.frame_callback:
                try:
                    self.frame_callback(frame.copy())
                except Exception as e:
                    logger.warning(f"Frame callback error: {e}")
            
            # Stable compression
            compressed_frame = self._compress_frame_stable(frame)
            
            if compressed_frame is not None:
                # Stable packet transmission with enhanced timestamps
                self._send_video_packet_stable_sequenced(compressed_frame, capture_timestamp, relative_timestamp)
            else:
                self.stats['frames_dropped'] += 1
            
        except Exception as e:
            logger.error(f"Stable frame processing error: {e}")
            self.stats['capture_errors'] += 1
    
    def _process_frame_extreme(self, frame: np.ndarray):
        """
        Process captured frame with extreme optimization for zero latency.
        
        Args:
            frame: Captured video frame from OpenCV
        """
        try:
            # Skip adaptive settings for maximum speed
            # Use fixed high-quality settings for LAN
            
            # Minimal frame processing - only resize if absolutely necessary
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            
            # Immediate local display callback
            if self.frame_callback:
                self.frame_callback(frame)
            
            # Ultra-fast compression with maximum quality for LAN
            compressed_frame = self._compress_frame_extreme(frame)
            
            if compressed_frame is not None:
                # Immediate packet transmission
                self._send_video_packet_extreme(compressed_frame)
            else:
                self.stats['frames_dropped'] += 1
            
        except Exception as e:
            self.stats['capture_errors'] += 1
    
    def _process_frame(self, frame: np.ndarray):
        """
        Process captured frame: resize, compress, and transmit with optimization.
        
        Args:
            frame: Captured video frame from OpenCV
        """
        try:
            capture_start_time = time.time()
            
            # Update adaptive settings periodically
            self._update_adaptive_settings()
            
            # Apply resolution scaling if needed
            target_width = int(self.width * self.adaptive_settings['resolution_scale'])
            target_height = int(self.height * self.adaptive_settings['resolution_scale'])
            
            # Resize frame with adaptive resolution
            if frame.shape[1] != target_width or frame.shape[0] != target_height:
                frame = cv2.resize(frame, (target_width, target_height))
            
            # Call frame callback for local display
            if self.frame_callback:
                try:
                    self.frame_callback(frame.copy())
                except Exception as e:
                    logger.warning(f"Error in frame callback: {e}")
            
            # Register capture timing
            video_optimizer.sync_manager.register_frame_timing(
                self.client_id, 'capture', capture_start_time, self.sequence_number
            )
            
            # Compress frame using adaptive quality
            encode_start_time = time.time()
            compressed_frame = self._compress_frame(frame)
            encode_time = time.time() - encode_start_time
            
            # Track encoding performance
            self.stats['encoding_times'].append(encode_time)
            if len(self.stats['encoding_times']) > 30:
                self.stats['encoding_times'] = self.stats['encoding_times'][-30:]
            
            # Register encode timing
            video_optimizer.sync_manager.register_frame_timing(
                self.client_id, 'encode', time.time(), self.sequence_number
            )
            
            if compressed_frame is not None:
                # Send compressed frame via UDP
                self._send_video_packet(compressed_frame)
            else:
                self.stats['frames_dropped'] += 1
            
            # Update performance metrics
            avg_encoding_time = sum(self.stats['encoding_times']) / len(self.stats['encoding_times']) if self.stats['encoding_times'] else 0
            video_optimizer.update_performance_metrics(self.stats['frames_dropped'], avg_encoding_time)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            self.stats['capture_errors'] += 1
    
    def _compress_frame_stable(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Stable frame compression with error handling.
        
        Args:
            frame: Video frame to compress
            
        Returns:
            bytes: Compressed frame data or None if compression failed
        """
        try:
            # Stable quality settings
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, 80,  # Good quality for stability
                cv2.IMWRITE_JPEG_OPTIMIZE, 1,  # Enable optimization
                cv2.IMWRITE_JPEG_PROGRESSIVE, 0  # Disable progressive for stability
            ]
            
            # Encode with error handling
            success, encoded_frame = cv2.imencode('.jpg', frame, encode_params)
            
            if success and encoded_frame is not None:
                compressed_data = encoded_frame.tobytes()
                
                # Update statistics
                self.stats['total_bytes_sent'] += len(compressed_data)
                
                return compressed_data
            else:
                logger.warning("Frame compression failed")
                return None
                
        except Exception as e:
            logger.error(f"Frame compression error: {e}")
            return None
    
    def _compress_frame_extreme(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Ultra-fast frame compression for extreme performance.
        
        Args:
            frame: Video frame to compress
            
        Returns:
            bytes: Compressed frame data or None if compression failed
        """
        try:
            # Ultra-high quality for LAN networks - no compression compromise
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, 95,  # Maximum quality
                cv2.IMWRITE_JPEG_OPTIMIZE, 0,  # Skip optimization for speed
                cv2.IMWRITE_JPEG_PROGRESSIVE, 0  # Skip progressive for speed
            ]
            
            # Immediate encoding without validation
            success, encoded_frame = cv2.imencode('.jpg', frame, encode_params)
            
            if success:
                compressed_data = encoded_frame.tobytes()
                
                # Minimal statistics update
                self.stats['total_bytes_sent'] += len(compressed_data)
                
                return compressed_data
            
            return None
                
        except:
            return None  # Fail silently for speed
    
    def _compress_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Compress video frame using adaptive JPEG compression.
        
        Args:
            frame: Video frame to compress
            
        Returns:
            bytes: Compressed frame data or None if compression failed
        """
        try:
            # Use adaptive quality setting
            current_quality = int(self.adaptive_settings['quality'])
            
            # JPEG compression parameters with adaptive quality
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, current_quality,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                cv2.IMWRITE_JPEG_PROGRESSIVE, 1  # Progressive JPEG for better streaming
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
    
    def _send_video_packet_stable_sequenced(self, compressed_frame: bytes, 
                                           capture_timestamp: float, relative_timestamp: float):
        """
        Send compressed video frame with sequencing timestamps.
        
        Args:
            compressed_frame: Compressed video frame data
            capture_timestamp: Absolute capture timestamp
            relative_timestamp: Relative timestamp from capture start
        """
        try:
            if not self.connection_manager:
                logger.warning("No connection manager available")
                return
            
            # Reasonable packet size for stability
            max_packet_size = 262144  # 256KB for stable transmission
            if len(compressed_frame) > max_packet_size:
                logger.warning(f"Frame too large ({len(compressed_frame)} bytes), skipping")
                return
            
            # Create packet with sequencing information
            with self._lock:
                try:
                    # Create enhanced video packet with timestamps
                    video_packet = MessageFactory.create_sequenced_video_packet(
                        sender_id=self.client_id,
                        sequence_num=self.sequence_number,
                        video_data=compressed_frame,
                        capture_timestamp=capture_timestamp,
                        relative_timestamp=relative_timestamp
                    )
                    self.sequence_number += 1
                except Exception as e:
                    logger.error(f"Error creating sequenced video packet: {e}")
                    # Fallback to regular packet
                    video_packet = MessageFactory.create_video_packet(
                        sender_id=self.client_id,
                        sequence_num=self.sequence_number,
                        video_data=compressed_frame
                    )
                    self.sequence_number += 1
            
            # Send with error handling
            try:
                success = self.connection_manager.send_udp_packet(video_packet)
                if success:
                    self.stats['frames_sent'] += 1
                else:
                    logger.warning("Failed to send sequenced video packet")
            except Exception as e:
                logger.error(f"Error sending sequenced video packet: {e}")
                
        except Exception as e:
            logger.error(f"Sequenced video packet transmission error: {e}")
    
    def _send_video_packet_stable(self, compressed_frame: bytes):
        """
        Send compressed video frame with stability optimization.
        
        Args:
            compressed_frame: Compressed video frame data
        """
        try:
            if not self.connection_manager:
                logger.warning("No connection manager available")
                return
            
            # Reasonable packet size for stability
            max_packet_size = 262144  # 256KB for stable transmission
            if len(compressed_frame) > max_packet_size:
                logger.warning(f"Frame too large ({len(compressed_frame)} bytes), skipping")
                return
            
            # Create packet with error handling
            with self._lock:
                try:
                    video_packet = MessageFactory.create_video_packet(
                        sender_id=self.client_id,
                        sequence_num=self.sequence_number,
                        video_data=compressed_frame
                    )
                    self.sequence_number += 1
                except Exception as e:
                    logger.error(f"Error creating video packet: {e}")
                    return
            
            # Send with error handling
            try:
                success = self.connection_manager.send_udp_packet(video_packet)
                if success:
                    self.stats['frames_sent'] += 1
                else:
                    logger.warning("Failed to send video packet")
            except Exception as e:
                logger.error(f"Error sending video packet: {e}")
                
        except Exception as e:
            logger.error(f"Stable video packet transmission error: {e}")
    
    def _send_video_packet_extreme(self, compressed_frame: bytes):
        """
        Send compressed video frame with extreme optimization.
        
        Args:
            compressed_frame: Compressed video frame data
        """
        try:
            if not self.connection_manager:
                return
            
            # Massive packet size for LAN - no limits for maximum speed
            max_packet_size = 524288  # 512KB for ultra-fast LAN transfer
            if len(compressed_frame) > max_packet_size:
                return  # Skip silently for speed
            
            # Immediate packet creation and transmission
            with self._lock:
                video_packet = MessageFactory.create_video_packet(
                    sender_id=self.client_id,
                    sequence_num=self.sequence_number,
                    video_data=compressed_frame
                )
                self.sequence_number += 1
            
            # Immediate transmission without error checking
            self.connection_manager.send_udp_packet(video_packet)
            self.stats['frames_sent'] += 1
                
        except:
            pass  # Ignore errors for maximum speed
    
    def _send_video_packet(self, compressed_frame: bytes):
        """
        Send compressed video frame as UDP packet.
        
        Args:
            compressed_frame: Compressed video frame data
        """
        try:
            if not self.connection_manager:
                return
            
            # Ultra-large packet size for LAN networks - no size restrictions
            max_packet_size = 131072  # 128KB maximum for ultra-fast LAN transfer
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