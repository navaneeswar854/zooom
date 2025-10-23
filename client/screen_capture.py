"""
Screen capture module for the collaboration client.
Handles screen/application window capture and compression for screen sharing.
"""

import threading
import time
import logging
import numpy as np
from typing import Optional, Callable, Tuple
from common.messages import TCPMessage, MessageType
from common.platform_utils import PLATFORM_INFO, ErrorHandler, is_windows, is_linux

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Platform-specific imports
SCREEN_CAPTURE_AVAILABLE = False
WINDOWS_SPECIFIC_AVAILABLE = False

try:
    import pyautogui
    SCREEN_CAPTURE_AVAILABLE = True
    logger.info("PyAutoGUI available for screen capture")
except ImportError:
    logger.warning("PyAutoGUI not available - screen capture disabled")

if is_windows():
    try:
        import pygetwindow as gw
        WINDOWS_SPECIFIC_AVAILABLE = True
        logger.info("Windows-specific screen capture features available")
    except ImportError:
        logger.warning("Windows screen capture dependencies not available")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available - screen compression may be limited")


class ScreenCapture:
    """
    Screen capture component for screen sharing functionality.
    
    Handles:
    - Screen/application window capture
    - Screen frame compression for TCP transmission
    - Cross-platform screen capture support
    """
    
    # Screen capture configuration constants
    DEFAULT_FPS = 2  # Very low FPS to prevent connection issues
    COMPRESSION_QUALITY = 30  # Lower quality to reduce frame size
    MAX_WIDTH = 800  # Smaller resolution to prevent large frames
    MAX_HEIGHT = 600
    
    def __init__(self, client_id: str, connection_manager=None):
        """
        Initialize the screen capture system.
        
        Args:
            client_id: Unique identifier for this client
            connection_manager: Connection manager for sending screen frames
        """
        self.client_id = client_id
        self.connection_manager = connection_manager
        
        # Screen capture state
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        
        # Capture settings
        self.fps = self.DEFAULT_FPS
        self.compression_quality = self.COMPRESSION_QUALITY
        self.capture_region = None  # None for full screen, (x, y, width, height) for region
        
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
        
        # Check platform capabilities
        self._check_capabilities()
    
    def _check_capabilities(self):
        """Check platform-specific screen capture capabilities."""
        self.platform = PLATFORM_INFO.system
        self.capture_available = PLATFORM_INFO.get_capability('screen_capture') and SCREEN_CAPTURE_AVAILABLE
        
        if not self.capture_available:
            logger.warning("Screen capture not available on this platform")
            return
        
        # Log platform-specific capabilities
        if is_windows() and WINDOWS_SPECIFIC_AVAILABLE:
            logger.info("Windows-specific window capture available")
        elif is_linux():
            logger.info("Linux screen capture available (full screen only)")
        else:
            logger.info("Basic screen capture available")
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """
        Set callback function to receive captured frames for local display.
        
        Args:
            callback: Function to call with captured frame data
        """
        self.frame_callback = callback
    
    def set_capture_settings(self, fps: int = None, quality: int = None, 
                           region: Tuple[int, int, int, int] = None):
        """
        Update screen capture settings.
        
        Args:
            fps: Frames per second for screen capture
            quality: JPEG compression quality (0-100)
            region: Capture region as (x, y, width, height) or None for full screen
        """
        with self._lock:
            if fps is not None:
                self.fps = max(1, min(15, fps))  # Clamp to reasonable range for screen sharing
            if quality is not None:
                self.compression_quality = max(10, min(100, quality))
            if region is not None:
                self.capture_region = region
        
        logger.info(f"Screen capture settings updated: {self.fps}fps, quality={self.compression_quality}")
    
    def start_capture(self) -> bool:
        """
        Start screen capture.
        
        Returns:
            bool: True if capture started successfully
        """
        if not self.capture_available:
            logger.error("Screen capture not available on this platform")
            return False
        
        if self.is_capturing:
            logger.warning("Screen capture already running")
            return True
        
        try:
            # Test screen capture capability
            test_screenshot = self._capture_screen()
            if test_screenshot is None:
                logger.error("Failed to capture test screenshot")
                return False
            
            # Start capture thread
            self.is_capturing = True
            self.stats['capture_start_time'] = time.time()
            self.sequence_number = 0
            
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()
            
            logger.info("Screen capture started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start screen capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop screen capture."""
        if not self.is_capturing:
            return
        
        logger.info("Stopping screen capture...")
        self.is_capturing = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        logger.info("Screen capture stopped")
    
    def _capture_loop(self):
        """Main screen capture loop running in separate thread."""
        logger.info("Screen capture loop started")
        
        frame_interval = 1.0 / self.fps  # Time between frames
        last_frame_time = 0
        
        while self.is_capturing:
            try:
                current_time = time.time()
                
                # Maintain frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                    continue
                
                # Capture screen
                screen_frame = self._capture_screen()
                
                if screen_frame is None:
                    logger.warning("Failed to capture screen")
                    self.stats['capture_errors'] += 1
                    time.sleep(0.1)  # Wait before retrying
                    continue
                
                # Process and send frame
                self._process_frame(screen_frame)
                
                last_frame_time = current_time
                self.stats['frames_captured'] += 1
                self.stats['last_frame_time'] = current_time
                
            except Exception as e:
                if self.is_capturing:  # Only log if we're still supposed to be capturing
                    logger.error(f"Error in screen capture loop: {e}")
                    self.stats['capture_errors'] += 1
                time.sleep(0.1)
        
        logger.info("Screen capture loop ended")
    
    def _capture_screen(self) -> Optional[np.ndarray]:
        """
        Capture screen or specified region.
        
        Returns:
            np.ndarray: Captured screen frame or None if capture failed
        """
        if not SCREEN_CAPTURE_AVAILABLE:
            logger.error("Screen capture not available")
            return None
        
        try:
            if self.capture_region:
                # Capture specific region
                x, y, width, height = self.capture_region
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
            else:
                # Capture full screen
                screenshot = pyautogui.screenshot()
            
            # Convert PIL image to numpy array
            frame_rgb = np.array(screenshot)
            
            # Convert to OpenCV format if available
            if OPENCV_AVAILABLE:
                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            else:
                # Use RGB format directly
                frame = frame_rgb
            
            # Resize if too large
            height, width = frame.shape[:2]
            if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                # Calculate scaling factor to fit within max dimensions
                scale_w = self.MAX_WIDTH / width
                scale_h = self.MAX_HEIGHT / height
                scale = min(scale_w, scale_h)
                
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                if OPENCV_AVAILABLE:
                    frame = cv2.resize(frame, (new_width, new_height))
                else:
                    # Fallback resize using PIL
                    from PIL import Image
                    pil_image = Image.fromarray(frame)
                    pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                    frame = np.array(pil_image)
            
            return frame
            
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            fix_suggestion = ErrorHandler.suggest_platform_fix(e)
            
            logger.error(f"Error capturing screen: {error_msg}")
            if fix_suggestion:
                logger.info(f"Suggested fix: {fix_suggestion}")
            
            return None
    
    def _process_frame(self, frame: np.ndarray):
        """
        Process captured frame: compress and transmit.
        
        Args:
            frame: Captured screen frame from screen capture
        """
        try:
            # Call frame callback for local display
            if self.frame_callback:
                try:
                    self.frame_callback(frame.copy())
                except Exception as e:
                    logger.warning(f"Error in frame callback: {e}")
            
            # Compress frame using JPEG
            compressed_frame = self._compress_frame(frame)
            
            if compressed_frame is not None:
                # Send compressed frame via TCP (for reliability)
                self._send_screen_frame(compressed_frame)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            self.stats['capture_errors'] += 1
    
    def _compress_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Compress screen frame using JPEG compression.
        
        Args:
            frame: Screen frame to compress
            
        Returns:
            bytes: Compressed frame data or None if compression failed
        """
        try:
            if OPENCV_AVAILABLE:
                # Use OpenCV for compression
                encode_params = [
                    cv2.IMWRITE_JPEG_QUALITY, self.compression_quality,
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1
                ]
                
                # Encode frame as JPEG
                success, encoded_frame = cv2.imencode('.jpg', frame, encode_params)
                
                if success:
                    compressed_data = encoded_frame.tobytes()
                else:
                    logger.warning("Failed to encode frame as JPEG with OpenCV")
                    return None
            else:
                # Fallback to PIL for compression
                from PIL import Image
                import io
                
                # Convert numpy array to PIL Image
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # RGB format
                    pil_image = Image.fromarray(frame, 'RGB')
                else:
                    # Grayscale or other format
                    pil_image = Image.fromarray(frame)
                
                # Compress using PIL
                buffer = io.BytesIO()
                pil_image.save(buffer, format='JPEG', quality=self.compression_quality, optimize=True)
                compressed_data = buffer.getvalue()
            
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
                
        except Exception as e:
            logger.error(f"Error compressing frame: {e}")
            return None
    
    def _send_screen_frame(self, compressed_frame: bytes):
        """
        Send compressed screen frame as TCP message.
        
        Args:
            compressed_frame: Compressed screen frame data
        """
        try:
            if not self.connection_manager:
                return
            
            # Create screen share TCP message
            with self._lock:
                screen_message = TCPMessage(
                    msg_type=MessageType.SCREEN_SHARE.value,
                    sender_id=self.client_id,
                    data={
                        'sequence_num': self.sequence_number,
                        'frame_data': compressed_frame.hex(),  # Convert bytes to hex string
                        'timestamp': time.time()
                    }
                )
                self.sequence_number += 1
            
            # Send message via connection manager
            success = self.connection_manager.send_tcp_message(screen_message)
            
            if success:
                self.stats['frames_sent'] += 1
            else:
                logger.warning("Failed to send screen frame")
                
        except Exception as e:
            logger.error(f"Error sending screen frame: {e}")
    
    def get_capture_stats(self) -> dict:
        """
        Get screen capture statistics.
        
        Returns:
            dict: Capture statistics and performance metrics
        """
        with self._lock:
            stats = self.stats.copy()
            stats['is_capturing'] = self.is_capturing
            stats['capture_available'] = self.capture_available
            stats['platform'] = self.platform
            stats['current_settings'] = {
                'fps': self.fps,
                'compression_quality': self.compression_quality,
                'capture_region': self.capture_region
            }
            
            if stats['capture_start_time']:
                stats['capture_duration'] = time.time() - stats['capture_start_time']
                
                # Calculate actual FPS
                if stats['capture_duration'] > 0:
                    stats['actual_fps'] = stats['frames_captured'] / stats['capture_duration']
            
            return stats
    
    def get_available_windows(self) -> list:
        """
        Get list of available application windows for capture.
        
        Returns:
            list: List of window information dictionaries
        """
        windows = []
        
        if not self.capture_available:
            return windows
        
        try:
            if is_windows() and WINDOWS_SPECIFIC_AVAILABLE:
                # Get all visible windows on Windows
                all_windows = gw.getAllWindows()
                for window in all_windows:
                    if window.visible and window.title.strip():
                        windows.append({
                            'title': window.title,
                            'left': window.left,
                            'top': window.top,
                            'width': window.width,
                            'height': window.height,
                            'platform_specific': True
                        })
            
            # Always add full screen option for all platforms
            if SCREEN_CAPTURE_AVAILABLE:
                screen_size = pyautogui.size()
                windows.append({
                    'title': 'Full Screen',
                    'left': 0,
                    'top': 0,
                    'width': screen_size.width,
                    'height': screen_size.height,
                    'platform_specific': False
                })
        
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            logger.error(f"Error getting available windows: {error_msg}")
        
        return windows
    
    def set_capture_window(self, window_title: str = None) -> bool:
        """
        Set capture to specific window or full screen.
        
        Args:
            window_title: Title of window to capture, None for full screen
            
        Returns:
            bool: True if window was found and set
        """
        try:
            if window_title is None or window_title == 'Full Screen':
                # Full screen capture
                self.capture_region = None
                logger.info("Set to full screen capture")
                return True
            
            if is_windows() and WINDOWS_SPECIFIC_AVAILABLE:
                # Find window by title on Windows
                windows = gw.getWindowsWithTitle(window_title)
                if windows:
                    window = windows[0]  # Take first match
                    self.capture_region = (window.left, window.top, window.width, window.height)
                    logger.info(f"Set capture to window: {window_title}")
                    return True
                else:
                    logger.warning(f"Window not found: {window_title}")
                    return False
            else:
                # Other platforms - only full screen supported
                logger.warning(f"Window-specific capture not supported on {self.platform}")
                logger.info("Falling back to full screen capture")
                self.capture_region = None
                return True
        
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            logger.error(f"Error setting capture window: {error_msg}")
            return False