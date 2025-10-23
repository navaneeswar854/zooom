"""
Cross-platform utility functions for the LAN Collaboration Suite.
Handles platform-specific operations and compatibility issues.
"""

import os
import sys
import platform
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlatformInfo:
    """Platform information and capability detection."""
    
    def __init__(self):
        self.system = platform.system()
        self.version = platform.version()
        self.architecture = platform.architecture()[0]
        self.python_version = sys.version_info
        
        # Detect capabilities
        self._detect_capabilities()
    
    def _detect_capabilities(self):
        """Detect platform-specific capabilities."""
        self.capabilities = {
            'audio_capture': self._check_audio_capability(),
            'video_capture': self._check_video_capability(),
            'screen_capture': self._check_screen_capture_capability(),
            'gui_framework': self._check_gui_capability(),
            'file_permissions': self._check_file_permissions(),
            'network_interfaces': self._check_network_capability()
        }
    
    def _check_audio_capability(self) -> bool:
        """Check if audio capture is available."""
        try:
            import pyaudio
            # Test PyAudio initialization
            pa = pyaudio.PyAudio()
            device_count = pa.get_device_count()
            pa.terminate()
            return device_count > 0
        except ImportError:
            logger.warning("PyAudio not available - audio features disabled")
            return False
        except Exception as e:
            logger.warning(f"Audio capability check failed: {e}")
            return False
    
    def _check_video_capability(self) -> bool:
        """Check if video capture is available."""
        try:
            import cv2
            # Test camera access
            cap = cv2.VideoCapture(0)
            is_available = cap.isOpened()
            cap.release()
            return is_available
        except ImportError:
            logger.warning("OpenCV not available - video features disabled")
            return False
        except Exception as e:
            logger.warning(f"Video capability check failed: {e}")
            return False
    
    def _check_screen_capture_capability(self) -> bool:
        """Check if screen capture is available."""
        try:
            if self.system == "Windows":
                # Check Windows-specific dependencies
                import pygetwindow as gw
                import pyautogui
                return True
            else:
                # Check cross-platform dependencies
                import pyautogui
                return True
        except ImportError:
            logger.warning("Screen capture dependencies not available")
            return False
        except Exception as e:
            logger.warning(f"Screen capture capability check failed: {e}")
            return False
    
    def _check_gui_capability(self) -> bool:
        """Check if GUI framework is available."""
        try:
            import tkinter
            # Test tkinter initialization
            root = tkinter.Tk()
            root.withdraw()  # Hide the window
            root.destroy()
            return True
        except ImportError:
            logger.error("Tkinter not available - GUI disabled")
            return False
        except Exception as e:
            logger.warning(f"GUI capability check failed: {e}")
            return False
    
    def _check_file_permissions(self) -> bool:
        """Check file system permissions."""
        try:
            # Test write permissions in current directory
            test_file = Path("test_permissions.tmp")
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception as e:
            logger.warning(f"File permission check failed: {e}")
            return False
    
    def _check_network_capability(self) -> bool:
        """Check network interface availability."""
        try:
            import socket
            # Test socket creation
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.close()
            return True
        except Exception as e:
            logger.warning(f"Network capability check failed: {e}")
            return False
    
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self.system == "Windows"
    
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self.system == "Linux"
    
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self.system == "Darwin"
    
    def get_capability(self, capability: str) -> bool:
        """Get specific capability status."""
        return self.capabilities.get(capability, False)
    
    def get_platform_summary(self) -> Dict:
        """Get platform information summary."""
        return {
            'system': self.system,
            'version': self.version,
            'architecture': self.architecture,
            'python_version': f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
            'capabilities': self.capabilities
        }


class PathUtils:
    """Cross-platform path utilities."""
    
    @staticmethod
    def get_safe_path(path: str) -> Path:
        """Get platform-safe path object."""
        return Path(path).resolve()
    
    @staticmethod
    def get_downloads_dir() -> Path:
        """Get platform-specific downloads directory."""
        if platform.system() == "Windows":
            # Windows downloads folder
            downloads = Path.home() / "Downloads"
        elif platform.system() == "Darwin":
            # macOS downloads folder
            downloads = Path.home() / "Downloads"
        else:
            # Linux downloads folder
            downloads = Path.home() / "Downloads"
            # Fallback to Desktop if Downloads doesn't exist
            if not downloads.exists():
                downloads = Path.home() / "Desktop"
        
        # Create directory if it doesn't exist
        downloads.mkdir(exist_ok=True)
        return downloads
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Get platform-specific temporary directory."""
        import tempfile
        return Path(tempfile.gettempdir())
    
    @staticmethod
    def get_app_data_dir(app_name: str = "LAN_Collaboration_Suite") -> Path:
        """Get platform-specific application data directory."""
        if platform.system() == "Windows":
            # Windows AppData folder
            app_data = Path(os.environ.get('APPDATA', Path.home() / "AppData" / "Roaming"))
        elif platform.system() == "Darwin":
            # macOS Application Support folder
            app_data = Path.home() / "Library" / "Application Support"
        else:
            # Linux config folder
            app_data = Path.home() / ".config"
        
        app_dir = app_data / app_name
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir
    
    @staticmethod
    def normalize_path_separators(path: str) -> str:
        """Normalize path separators for current platform."""
        return str(Path(path))
    
    @staticmethod
    def is_path_safe(path: str) -> bool:
        """Check if path is safe (no directory traversal)."""
        try:
            resolved_path = Path(path).resolve()
            # Check for directory traversal attempts
            return ".." not in str(resolved_path)
        except Exception:
            return False


class NetworkUtils:
    """Cross-platform network utilities."""
    
    @staticmethod
    def get_local_ip() -> str:
        """Get local IP address."""
        try:
            import socket
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    @staticmethod
    def get_available_port(start_port: int = 8080) -> int:
        """Find an available port starting from the given port."""
        import socket
        
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        
        raise RuntimeError("No available ports found")
    
    @staticmethod
    def configure_socket_options(sock, socket_type: str = "tcp"):
        """Configure platform-specific socket options."""
        import socket
        
        try:
            # Common socket options
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Platform-specific optimizations
            if platform.system() == "Windows":
                # Windows-specific socket options
                if socket_type.lower() == "tcp":
                    # Disable Nagle's algorithm for low latency
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                elif socket_type.lower() == "udp":
                    # Set larger buffer sizes for media streaming
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
            elif platform.system() == "Linux":
                # Linux-specific socket options
                if socket_type.lower() == "tcp":
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    # Enable keep-alive
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                elif socket_type.lower() == "udp":
                    # Set buffer sizes
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
        except Exception as e:
            logger.warning(f"Failed to configure socket options: {e}")


class DeviceUtils:
    """Cross-platform device access utilities."""
    
    @staticmethod
    def get_audio_devices() -> List[Dict]:
        """Get available audio input devices."""
        devices = []
        
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
            
            pa.terminate()
            
        except Exception as e:
            logger.warning(f"Failed to enumerate audio devices: {e}")
        
        return devices
    
    @staticmethod
    def get_video_devices() -> List[Dict]:
        """Get available video capture devices."""
        devices = []
        
        try:
            import cv2
            
            # Test camera indices 0-5
            for i in range(6):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    devices.append({
                        'index': i,
                        'name': f"Camera {i}",
                        'width': width,
                        'height': height,
                        'fps': fps
                    })
                
                cap.release()
            
        except Exception as e:
            logger.warning(f"Failed to enumerate video devices: {e}")
        
        return devices
    
    @staticmethod
    def test_device_access() -> Dict[str, bool]:
        """Test access to various device types."""
        results = {
            'audio_input': False,
            'video_input': False,
            'screen_capture': False
        }
        
        # Test audio input
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            if pa.get_device_count() > 0:
                results['audio_input'] = True
            pa.terminate()
        except Exception:
            pass
        
        # Test video input
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                results['video_input'] = True
            cap.release()
        except Exception:
            pass
        
        # Test screen capture
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            if screenshot:
                results['screen_capture'] = True
        except Exception:
            pass
        
        return results


class ErrorHandler:
    """Cross-platform error handling utilities."""
    
    @staticmethod
    def get_platform_specific_error_message(error: Exception) -> str:
        """Get platform-specific error message."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Platform-specific error handling
        if platform.system() == "Windows":
            if "WinError" in error_msg:
                return f"Windows system error: {error_msg}"
            elif "PermissionError" in error_type:
                return "Permission denied. Try running as administrator."
        
        elif platform.system() == "Linux":
            if "Permission denied" in error_msg:
                return "Permission denied. Check file/device permissions."
            elif "No such device" in error_msg:
                return "Device not found. Check if device is connected and drivers are installed."
        
        # Generic error message
        return f"{error_type}: {error_msg}"
    
    @staticmethod
    def suggest_platform_fix(error: Exception) -> Optional[str]:
        """Suggest platform-specific fixes for common errors."""
        error_msg = str(error).lower()
        
        if platform.system() == "Windows":
            if "access denied" in error_msg or "permission" in error_msg:
                return "Try running the application as administrator"
            elif "audio" in error_msg and "device" in error_msg:
                return "Check Windows audio settings and ensure microphone permissions are granted"
            elif "camera" in error_msg or "video" in error_msg:
                return "Check Windows camera settings and ensure camera permissions are granted"
        
        elif platform.system() == "Linux":
            if "permission denied" in error_msg:
                return "Add user to audio/video groups: sudo usermod -a -G audio,video $USER"
            elif "audio" in error_msg:
                return "Install ALSA/PulseAudio: sudo apt-get install alsa-utils pulseaudio"
            elif "video" in error_msg:
                return "Install V4L2 utils: sudo apt-get install v4l-utils"
        
        return None


# Global platform info instance
PLATFORM_INFO = PlatformInfo()

# Convenience functions
def is_windows() -> bool:
    """Check if running on Windows."""
    return PLATFORM_INFO.is_windows()

def is_linux() -> bool:
    """Check if running on Linux."""
    return PLATFORM_INFO.is_linux()

def is_macos() -> bool:
    """Check if running on macOS."""
    return PLATFORM_INFO.is_macos()

def get_platform_capabilities() -> Dict:
    """Get platform capabilities."""
    return PLATFORM_INFO.capabilities

def log_platform_info():
    """Log platform information for debugging."""
    info = PLATFORM_INFO.get_platform_summary()
    logger.info(f"Platform: {info['system']} {info['version']} ({info['architecture']})")
    logger.info(f"Python: {info['python_version']}")
    logger.info(f"Capabilities: {info['capabilities']}")