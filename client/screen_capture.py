"""
Screen capture module for the collaboration client.
Handles screen/application window capture and compression for screen sharing.
"""

import threading
import time
import logging
import os
import numpy as np
from typing import Optional, Callable, Tuple
from common.messages import TCPMessage, MessageType
from common.platform_utils import PLATFORM_INFO, ErrorHandler, is_windows, is_linux, is_macos

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
        """Check platform-specific screen capture capabilities and permissions."""
        self.platform = PLATFORM_INFO.system
        
        # Perform comprehensive capability check
        capability_result = self._check_platform_capabilities()
        permission_result = self._check_screen_capture_permissions()
        
        self.capture_available = capability_result['available'] and permission_result['available']
        self.capability_details = capability_result
        self.permission_details = permission_result
        
        if not self.capture_available:
            logger.warning("Screen capture not available on this platform")
            if not capability_result['available']:
                logger.warning(f"Capability issue: {capability_result['message']}")
            if not permission_result['available']:
                logger.warning(f"Permission issue: {permission_result['message']}")
            return
        
        # Log platform-specific capabilities
        if is_windows() and WINDOWS_SPECIFIC_AVAILABLE:
            logger.info("Windows-specific window capture available")
        elif is_linux():
            logger.info("Linux screen capture available (full screen only)")
        else:
            logger.info("Basic screen capture available")
    
    def _check_platform_capabilities(self) -> dict:
        """
        Check platform-specific screen capture capabilities.
        
        Returns:
            dict: Capability check results with details
        """
        result = {
            'available': False,
            'message': '',
            'dependencies': [],
            'missing_dependencies': [],
            'platform_specific': {}
        }
        
        # Check basic dependencies
        if not SCREEN_CAPTURE_AVAILABLE:
            result['missing_dependencies'].append('pyautogui')
            result['message'] = "PyAutoGUI not available - required for screen capture"
            return result
        
        result['dependencies'].append('pyautogui')
        
        # Check platform-specific capabilities
        if is_windows():
            result['platform_specific'] = self._check_windows_capabilities()
        elif is_linux():
            result['platform_specific'] = self._check_linux_capabilities()
        elif is_macos():
            result['platform_specific'] = self._check_macos_capabilities()
        else:
            result['platform_specific'] = {'supported': False, 'message': 'Unsupported platform'}
        
        # Check if PIL/Pillow is available for image processing
        try:
            from PIL import Image
            result['dependencies'].append('pillow')
        except ImportError:
            result['missing_dependencies'].append('pillow')
        
        # Check if OpenCV is available for advanced processing
        if OPENCV_AVAILABLE:
            result['dependencies'].append('opencv-python')
        
        # Overall availability
        result['available'] = (
            len(result['missing_dependencies']) == 0 and 
            result['platform_specific'].get('supported', False)
        )
        
        if result['available']:
            result['message'] = "All screen capture capabilities available"
        else:
            missing = ', '.join(result['missing_dependencies'])
            platform_msg = result['platform_specific'].get('message', '')
            result['message'] = f"Missing dependencies: {missing}. {platform_msg}".strip()
        
        return result
    
    def _check_windows_capabilities(self) -> dict:
        """Check Windows-specific screen capture capabilities."""
        result = {'supported': True, 'features': [], 'issues': []}
        
        # Check for Windows-specific window capture
        if WINDOWS_SPECIFIC_AVAILABLE:
            result['features'].append('window_specific_capture')
        else:
            result['issues'].append('pygetwindow not available - window-specific capture disabled')
        
        # Check for PIL ImageGrab (Windows native)
        try:
            from PIL import ImageGrab
            result['features'].append('pil_imagegrab')
        except ImportError:
            result['issues'].append('PIL ImageGrab not available')
        
        # Check display availability
        try:
            import pyautogui
            screen_size = pyautogui.size()
            if screen_size.width > 0 and screen_size.height > 0:
                result['features'].append('display_available')
            else:
                result['issues'].append('No display detected')
                result['supported'] = False
        except Exception as e:
            result['issues'].append(f'Display check failed: {e}')
            result['supported'] = False
        
        result['message'] = f"Windows features: {result['features']}, Issues: {result['issues']}"
        return result
    
    def _check_linux_capabilities(self) -> dict:
        """Check Linux-specific screen capture capabilities."""
        result = {'supported': True, 'features': [], 'issues': []}
        
        # Check X11 display
        display = os.environ.get('DISPLAY')
        if not display:
            result['issues'].append('DISPLAY environment variable not set')
            result['supported'] = False
        else:
            result['features'].append(f'x11_display_{display}')
        
        # Check for scrot command (Linux fallback)
        try:
            import subprocess
            subprocess.run(['which', 'scrot'], capture_output=True, check=True)
            result['features'].append('scrot_available')
        except (subprocess.CalledProcessError, FileNotFoundError):
            result['issues'].append('scrot not available - install with: sudo apt-get install scrot')
        
        # Check for xvfb (headless support)
        try:
            import subprocess
            subprocess.run(['which', 'xvfb-run'], capture_output=True, check=True)
            result['features'].append('xvfb_available')
        except (subprocess.CalledProcessError, FileNotFoundError):
            result['issues'].append('xvfb-run not available - install with: sudo apt-get install xvfb')
        
        result['message'] = f"Linux features: {result['features']}, Issues: {result['issues']}"
        return result
    
    def _check_macos_capabilities(self) -> dict:
        """Check macOS-specific screen capture capabilities."""
        result = {'supported': True, 'features': [], 'issues': []}
        
        # Check for PIL ImageGrab (macOS support)
        try:
            from PIL import ImageGrab
            result['features'].append('pil_imagegrab')
        except ImportError:
            result['issues'].append('PIL ImageGrab not available')
        
        # Check display availability
        try:
            import pyautogui
            screen_size = pyautogui.size()
            if screen_size.width > 0 and screen_size.height > 0:
                result['features'].append('display_available')
            else:
                result['issues'].append('No display detected')
                result['supported'] = False
        except Exception as e:
            result['issues'].append(f'Display check failed: {e}')
            result['supported'] = False
        
        result['message'] = f"macOS features: {result['features']}, Issues: {result['issues']}"
        return result
    
    def _check_screen_capture_permissions(self) -> dict:
        """
        Check screen capture permissions on the current platform.
        
        Returns:
            dict: Permission check results with details
        """
        result = {
            'available': False,
            'message': '',
            'permission_type': '',
            'suggestions': []
        }
        
        if is_windows():
            result = self._check_windows_permissions()
        elif is_linux():
            result = self._check_linux_permissions()
        elif is_macos():
            result = self._check_macos_permissions()
        else:
            result['message'] = 'Permission check not implemented for this platform'
            result['available'] = True  # Assume available for unknown platforms
        
        return result
    
    def _check_windows_permissions(self) -> dict:
        """Check Windows screen capture permissions."""
        result = {
            'available': True,
            'message': 'Windows screen capture permissions OK',
            'permission_type': 'windows_screen_recording',
            'suggestions': []
        }
        
        try:
            # Test actual screen capture to check permissions
            import pyautogui
            test_screenshot = pyautogui.screenshot()
            
            if test_screenshot is None or test_screenshot.size == (0, 0):
                result['available'] = False
                result['message'] = 'Screen capture permission denied or screen locked'
                result['suggestions'] = [
                    'Enable screen recording permissions in Windows Privacy Settings',
                    'Go to Settings > Privacy > Screen recording and allow the application',
                    'Ensure screen is not locked or in sleep mode',
                    'Try running as administrator'
                ]
        
        except PermissionError:
            result['available'] = False
            result['message'] = 'Screen capture access denied'
            result['suggestions'] = [
                'Run application as administrator',
                'Check Windows Privacy Settings > Screen recording',
                'Disable Windows Defender real-time protection temporarily'
            ]
        
        except Exception as e:
            if 'access' in str(e).lower() or 'permission' in str(e).lower():
                result['available'] = False
                result['message'] = f'Permission error: {e}'
                result['suggestions'] = [
                    'Check Windows Privacy Settings > Screen recording',
                    'Run application as administrator'
                ]
        
        return result
    
    def _check_linux_permissions(self) -> dict:
        """Check Linux screen capture permissions."""
        result = {
            'available': True,
            'message': 'Linux screen capture permissions OK',
            'permission_type': 'x11_display_access',
            'suggestions': []
        }
        
        try:
            # Check DISPLAY environment variable
            display = os.environ.get('DISPLAY')
            if not display:
                result['available'] = False
                result['message'] = 'DISPLAY environment variable not set'
                result['suggestions'] = [
                    'Set DISPLAY environment variable: export DISPLAY=:0',
                    'Use xvfb-run for headless environments: xvfb-run -a python script.py',
                    'Ensure X11 server is running'
                ]
                return result
            
            # Test actual screen capture
            import pyautogui
            test_screenshot = pyautogui.screenshot()
            
            if test_screenshot is None or test_screenshot.size == (0, 0):
                result['available'] = False
                result['message'] = 'Screen capture failed - permission or display issue'
                result['suggestions'] = [
                    'Add user to video group: sudo usermod -a -G video $USER',
                    'Install required packages: sudo apt-get install python3-tk scrot',
                    'Check X11 permissions: xhost +local:',
                    'For headless: use xvfb-run'
                ]
        
        except PermissionError:
            result['available'] = False
            result['message'] = 'Screen capture permission denied'
            result['suggestions'] = [
                'Add user to video group: sudo usermod -a -G video $USER',
                'Run with sudo (not recommended for production)',
                'Check X11 permissions: xhost +local:'
            ]
        
        except Exception as e:
            if 'display' in str(e).lower() or 'x11' in str(e).lower():
                result['available'] = False
                result['message'] = f'X11 display error: {e}'
                result['suggestions'] = [
                    'Ensure X11 server is running',
                    'Set DISPLAY variable: export DISPLAY=:0',
                    'Use xvfb-run for headless: xvfb-run -a python script.py'
                ]
        
        return result
    
    def _check_macos_permissions(self) -> dict:
        """Check macOS screen capture permissions."""
        result = {
            'available': True,
            'message': 'macOS screen capture permissions OK',
            'permission_type': 'macos_screen_recording',
            'suggestions': []
        }
        
        try:
            # Test actual screen capture
            import pyautogui
            test_screenshot = pyautogui.screenshot()
            
            if test_screenshot is None or test_screenshot.size == (0, 0):
                result['available'] = False
                result['message'] = 'Screen capture permission denied'
                result['suggestions'] = [
                    'Enable screen recording permissions in System Preferences',
                    'Go to System Preferences > Security & Privacy > Privacy > Screen Recording',
                    'Add your application to the allowed list',
                    'Restart the application after granting permissions'
                ]
        
        except PermissionError:
            result['available'] = False
            result['message'] = 'Screen capture access denied'
            result['suggestions'] = [
                'Grant screen recording permissions in System Preferences',
                'System Preferences > Security & Privacy > Privacy > Screen Recording',
                'Click the lock to make changes and add your application'
            ]
        
        except Exception as e:
            if 'permission' in str(e).lower() or 'access' in str(e).lower():
                result['available'] = False
                result['message'] = f'Permission error: {e}'
                result['suggestions'] = [
                    'Check System Preferences > Security & Privacy > Privacy > Screen Recording',
                    'Ensure application has screen recording permissions'
                ]
        
        return result
    
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
    
    def start_capture(self) -> tuple[bool, str]:
        """
        Start screen capture with detailed error reporting.
        
        Returns:
            tuple[bool, str]: (success, detailed_message)
        """
        logger.info("Starting screen capture...")
        
        # Check platform availability first
        if not self.capture_available:
            error_msg = self._get_platform_unavailable_message()
            logger.error(error_msg)
            return False, error_msg
        
        if self.is_capturing:
            logger.warning("Screen capture already running")
            return True, "Screen capture already active"
        
        try:
            # Test screen capture capability with detailed error reporting
            test_result, test_message = self._test_screen_capture()
            if not test_result:
                logger.error(f"Screen capture test failed: {test_message}")
                return False, test_message
            
            # Start capture thread
            self.is_capturing = True
            self.stats['capture_start_time'] = time.time()
            self.sequence_number = 0
            
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()
            
            success_msg = "Screen capture started successfully"
            logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = self._get_detailed_error_message(e)
            logger.error(f"Failed to start screen capture: {error_msg}")
            return False, error_msg
    
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
        Capture screen or specified region with fallback options.
        
        Returns:
            np.ndarray: Captured screen frame or None if all methods failed
        """
        if not SCREEN_CAPTURE_AVAILABLE:
            logger.error("Screen capture not available")
            return None
        
        # Try primary method first
        frame = self._capture_screen_primary()
        if frame is not None:
            return frame
        
        # Try fallback methods
        logger.warning("Primary screen capture failed, trying fallback methods...")
        
        frame = self._capture_screen_fallback()
        if frame is not None:
            logger.info("Fallback screen capture successful")
            return frame
        
        logger.error("All screen capture methods failed")
        return None
    
    def _capture_screen_primary(self) -> Optional[np.ndarray]:
        """
        Primary screen capture method using pyautogui.
        
        Returns:
            np.ndarray: Captured screen frame or None if failed
        """
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
            frame = self._resize_frame_if_needed(frame)
            return frame
            
        except Exception as e:
            error_msg = ErrorHandler.get_platform_specific_error_message(e)
            fix_suggestion = ErrorHandler.suggest_platform_fix(e)
            
            logger.warning(f"Primary screen capture failed: {error_msg}")
            if fix_suggestion:
                logger.info(f"Suggested fix: {fix_suggestion}")
            
            return None
    
    def _capture_screen_fallback(self) -> Optional[np.ndarray]:
        """
        Fallback screen capture methods for different platforms.
        
        Returns:
            np.ndarray: Captured screen frame or None if failed
        """
        # Try platform-specific fallback methods
        if is_windows():
            return self._capture_screen_windows_fallback()
        elif is_linux():
            return self._capture_screen_linux_fallback()
        else:
            return self._capture_screen_generic_fallback()
    
    def _capture_screen_windows_fallback(self) -> Optional[np.ndarray]:
        """
        Windows-specific fallback screen capture methods.
        
        Returns:
            np.ndarray: Captured screen frame or None if failed
        """
        try:
            # Try using PIL ImageGrab directly (Windows only)
            from PIL import ImageGrab
            
            if self.capture_region:
                x, y, width, height = self.capture_region
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            else:
                screenshot = ImageGrab.grab()
            
            if screenshot:
                frame_rgb = np.array(screenshot)
                if OPENCV_AVAILABLE:
                    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                else:
                    frame = frame_rgb
                
                frame = self._resize_frame_if_needed(frame)
                logger.info("Windows ImageGrab fallback successful")
                return frame
                
        except Exception as e:
            logger.warning(f"Windows ImageGrab fallback failed: {e}")
        
        return None
    
    def _capture_screen_linux_fallback(self) -> Optional[np.ndarray]:
        """
        Linux-specific fallback screen capture methods.
        
        Returns:
            np.ndarray: Captured screen frame or None if failed
        """
        try:
            # Try using scrot command line tool
            import subprocess
            import tempfile
            import os
            from PIL import Image
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Use scrot to capture screen
                if self.capture_region:
                    x, y, width, height = self.capture_region
                    cmd = ['scrot', '-a', f'{x},{y},{width},{height}', tmp_path]
                else:
                    cmd = ['scrot', tmp_path]
                
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                
                if result.returncode == 0 and os.path.exists(tmp_path):
                    # Load captured image
                    screenshot = Image.open(tmp_path)
                    frame_rgb = np.array(screenshot)
                    
                    if OPENCV_AVAILABLE:
                        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                    else:
                        frame = frame_rgb
                    
                    frame = self._resize_frame_if_needed(frame)
                    logger.info("Linux scrot fallback successful")
                    return frame
                    
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.warning(f"Linux scrot fallback failed: {e}")
        
        return None
    
    def _capture_screen_generic_fallback(self) -> Optional[np.ndarray]:
        """
        Generic fallback screen capture method.
        
        Returns:
            np.ndarray: Captured screen frame or None if failed
        """
        try:
            # Try using PIL ImageGrab (cross-platform but limited)
            from PIL import ImageGrab
            
            # ImageGrab.grab() without bbox for full screen
            screenshot = ImageGrab.grab()
            
            if screenshot:
                frame_rgb = np.array(screenshot)
                if OPENCV_AVAILABLE:
                    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                else:
                    frame = frame_rgb
                
                frame = self._resize_frame_if_needed(frame)
                logger.info("Generic PIL ImageGrab fallback successful")
                return frame
                
        except Exception as e:
            logger.warning(f"Generic fallback failed: {e}")
        
        return None
    
    def _resize_frame_if_needed(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize frame if it exceeds maximum dimensions.
        
        Args:
            frame: Input frame to resize
            
        Returns:
            np.ndarray: Resized frame
        """
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
    
    def get_capability_info(self) -> dict:
        """
        Get detailed capability and permission information.
        
        Returns:
            dict: Comprehensive capability and permission details
        """
        return {
            'platform': self.platform,
            'capture_available': self.capture_available,
            'capabilities': getattr(self, 'capability_details', {}),
            'permissions': getattr(self, 'permission_details', {}),
            'dependencies': {
                'pyautogui': SCREEN_CAPTURE_AVAILABLE,
                'opencv': OPENCV_AVAILABLE,
                'windows_specific': WINDOWS_SPECIFIC_AVAILABLE if is_windows() else None
            }
        }
    
    def get_setup_instructions(self) -> list:
        """
        Get platform-specific setup instructions for screen capture.
        
        Returns:
            list: List of setup instruction strings
        """
        instructions = []
        
        if self.capture_available:
            instructions.append("✓ Screen capture is ready to use")
            return instructions
        
        # Add capability-specific instructions
        if hasattr(self, 'capability_details') and not self.capability_details['available']:
            missing_deps = self.capability_details.get('missing_dependencies', [])
            if missing_deps:
                deps_str = ' '.join(missing_deps)
                instructions.append(f"Install missing dependencies: pip install {deps_str}")
        
        # Add permission-specific instructions
        if hasattr(self, 'permission_details') and not self.permission_details['available']:
            suggestions = self.permission_details.get('suggestions', [])
            for suggestion in suggestions:
                instructions.append(f"• {suggestion}")
        
        # Add platform-specific instructions
        if is_windows():
            instructions.extend([
                "Windows Setup:",
                "• Install dependencies: pip install pyautogui pygetwindow pillow",
                "• Enable screen recording in Privacy Settings",
                "• Run as administrator if needed"
            ])
        elif is_linux():
            instructions.extend([
                "Linux Setup:",
                "• Install system packages: sudo apt-get install python3-tk scrot xvfb",
                "• Install Python packages: pip install pyautogui pillow",
                "• Add user to video group: sudo usermod -a -G video $USER",
                "• Set DISPLAY variable: export DISPLAY=:0"
            ])
        elif is_macos():
            instructions.extend([
                "macOS Setup:",
                "• Install dependencies: pip install pyautogui pillow",
                "• Grant screen recording permissions in System Preferences",
                "• System Preferences > Security & Privacy > Privacy > Screen Recording"
            ])
        
        return instructions
    
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
    
    def _get_platform_unavailable_message(self) -> str:
        """
        Get detailed message for platform unavailability.
        
        Returns:
            str: Detailed error message with platform-specific suggestions
        """
        if not SCREEN_CAPTURE_AVAILABLE:
            if is_windows():
                return ("Screen capture not available. Please install required dependencies: "
                       "pip install pyautogui pygetwindow pillow")
            elif is_linux():
                return ("Screen capture not available. Please install required dependencies: "
                       "pip install pyautogui pillow. On Linux, you may also need: "
                       "sudo apt-get install python3-tk python3-dev scrot")
            else:
                return ("Screen capture not available. Please install required dependencies: "
                       "pip install pyautogui pillow")
        
        return f"Screen capture not supported on {self.platform}"
    
    def _test_screen_capture(self) -> tuple[bool, str]:
        """
        Test screen capture capability with detailed error reporting.
        
        Returns:
            tuple[bool, str]: (success, detailed_message)
        """
        try:
            # Test basic screen capture
            test_screenshot = self._capture_screen()
            if test_screenshot is None:
                return False, "Failed to capture test screenshot - check screen capture permissions"
            
            # Test image processing
            if test_screenshot.size == 0:
                return False, "Captured empty screenshot - screen may be locked or unavailable"
            
            # Test compression capability
            compressed = self._compress_frame(test_screenshot)
            if compressed is None:
                return False, "Failed to compress test screenshot - image processing error"
            
            return True, "Screen capture test successful"
            
        except PermissionError:
            if is_windows():
                return False, ("Screen capture permission denied. Please enable screen recording "
                             "permissions in Windows Privacy Settings > Screen recording")
            elif is_linux():
                return False, ("Screen capture permission denied. Please run with appropriate "
                             "permissions or install xvfb-run for headless environments")
            else:
                return False, "Screen capture permission denied. Please check system permissions"
        
        except ImportError as e:
            missing_module = str(e).split("'")[1] if "'" in str(e) else "unknown"
            return False, f"Missing required module: {missing_module}. Please install with: pip install {missing_module}"
        
        except Exception as e:
            return False, self._get_detailed_error_message(e)
    
    def _get_detailed_error_message(self, error: Exception) -> str:
        """
        Get detailed error message with platform-specific suggestions.
        
        Args:
            error: Exception that occurred
            
        Returns:
            str: Detailed error message with suggestions
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Platform-specific error handling
        if is_windows():
            if "access denied" in error_msg or "permission" in error_msg:
                return ("Screen capture access denied. Please run as administrator or enable "
                       "screen recording permissions in Windows Privacy Settings")
            elif "display" in error_msg or "screen" in error_msg:
                return ("Screen display error. Please check if screen is available and not locked")
            elif "module" in error_msg or "import" in error_msg:
                return ("Missing dependencies. Please install: pip install pyautogui pygetwindow pillow")
        
        elif is_linux():
            if "permission denied" in error_msg:
                return ("Permission denied. Please run with sudo or add user to video group: "
                       "sudo usermod -a -G video $USER")
            elif "display" in error_msg or "x11" in error_msg:
                return ("X11 display error. Please ensure DISPLAY is set or use xvfb-run for headless mode")
            elif "module" in error_msg or "import" in error_msg:
                return ("Missing dependencies. Please install: sudo apt-get install python3-tk scrot && "
                       "pip install pyautogui pillow")
        
        else:  # macOS or other
            if "permission" in error_msg:
                return ("Screen capture permission denied. Please enable screen recording permissions "
                       "in System Preferences > Security & Privacy > Privacy > Screen Recording")
        
        # Generic error with suggestion
        suggestion = ErrorHandler.suggest_platform_fix(error)
        if suggestion:
            return f"{error_type}: {error}. Suggestion: {suggestion}"
        
        return f"{error_type}: {error}"
    
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