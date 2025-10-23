#!/usr/bin/env python3
"""
Cross-platform startup script for the LAN Collaboration Suite client.
Handles platform-specific initialization and dependency checking.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        logger.error("Python 3.7 or higher is required")
        return False
    
    logger.info(f"Python version: {sys.version}")
    return True


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    optional_deps = []
    
    # Core dependencies
    try:
        import tkinter
        logger.info("✓ GUI framework (tkinter) available")
    except ImportError:
        missing_deps.append("tkinter")
        logger.error("✗ GUI framework (tkinter) not available")
    
    # Audio dependencies
    try:
        import pyaudio
        logger.info("✓ Audio capture (pyaudio) available")
    except ImportError:
        optional_deps.append("pyaudio")
        logger.warning("✗ Audio capture (pyaudio) not available - audio features disabled")
    
    # Video dependencies
    try:
        import cv2
        logger.info("✓ Video capture (opencv-python) available")
    except ImportError:
        optional_deps.append("opencv-python")
        logger.warning("✗ Video capture (opencv-python) not available - video features disabled")
    
    # Screen capture dependencies
    try:
        import pyautogui
        logger.info("✓ Screen capture (pyautogui) available")
    except ImportError:
        optional_deps.append("pyautogui")
        logger.warning("✗ Screen capture (pyautogui) not available - screen sharing disabled")
    
    # Platform-specific dependencies
    if sys.platform == "win32":
        try:
            import pygetwindow
            logger.info("✓ Windows window management (pygetwindow) available")
        except ImportError:
            optional_deps.append("pygetwindow")
            logger.warning("✗ Windows window management not available - limited screen sharing")
    
    if missing_deps:
        logger.error(f"Missing required dependencies: {', '.join(missing_deps)}")
        logger.error("Please install missing dependencies and try again")
        return False
    
    if optional_deps:
        logger.warning(f"Missing optional dependencies: {', '.join(optional_deps)}")
        logger.warning("Some features may be disabled")
    
    return True


def setup_platform_environment():
    """Setup platform-specific environment."""
    from common.platform_utils import PLATFORM_INFO, log_platform_info
    
    # Log platform information
    log_platform_info()
    
    # Platform-specific setup
    if PLATFORM_INFO.is_windows():
        logger.info("Setting up Windows environment...")
        # Windows-specific setup if needed
        
    elif PLATFORM_INFO.is_linux():
        logger.info("Setting up Linux environment...")
        # Linux-specific setup if needed
        
    elif PLATFORM_INFO.is_macos():
        logger.info("Setting up macOS environment...")
        # macOS-specific setup if needed
    
    return True


def main():
    """Main startup function."""
    logger.info("Starting LAN Collaboration Suite Client...")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Setup platform environment
    if not setup_platform_environment():
        logger.error("Platform setup failed")
        sys.exit(1)
    
    try:
        # Import and start the client
        from client.main_client import CollaborationClient
        
        logger.info("Initializing client...")
        client = CollaborationClient()
        
        logger.info("Starting client application...")
        client.run()
        
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
    except Exception as e:
        logger.error(f"Client startup failed: {e}")
        logger.exception("Full error details:")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()