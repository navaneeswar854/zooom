#!/usr/bin/env python3
"""
Debug script to test screen capture functionality.
"""

import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pyautogui():
    """Test PyAutoGUI screen capture."""
    try:
        import pyautogui
        logger.info("✓ PyAutoGUI imported successfully")
        
        # Test screen size
        screen_size = pyautogui.size()
        logger.info(f"Screen size: {screen_size}")
        
        if screen_size.width == 0 or screen_size.height == 0:
            logger.error("❌ Screen size is 0x0 - no display detected")
            return False
        
        # Test screenshot
        logger.info("Taking test screenshot...")
        screenshot = pyautogui.screenshot()
        
        if screenshot is None:
            logger.error("❌ Screenshot returned None")
            return False
        
        if screenshot.size == (0, 0):
            logger.error("❌ Screenshot size is 0x0")
            return False
        
        logger.info(f"✓ Screenshot successful: {screenshot.size}")
        return True
        
    except ImportError as e:
        logger.error(f"❌ PyAutoGUI import failed: {e}")
        return False
    except PermissionError as e:
        logger.error(f"❌ Permission error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Screenshot failed: {e}")
        return False


def test_pil_imagegrab():
    """Test PIL ImageGrab (Windows native)."""
    try:
        from PIL import ImageGrab
        logger.info("✓ PIL ImageGrab imported successfully")
        
        # Test screenshot
        logger.info("Taking PIL test screenshot...")
        screenshot = ImageGrab.grab()
        
        if screenshot is None:
            logger.error("❌ PIL screenshot returned None")
            return False
        
        if screenshot.size == (0, 0):
            logger.error("❌ PIL screenshot size is 0x0")
            return False
        
        logger.info(f"✓ PIL screenshot successful: {screenshot.size}")
        return True
        
    except ImportError as e:
        logger.error(f"❌ PIL ImageGrab import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ PIL screenshot failed: {e}")
        return False


def test_screen_capture_class():
    """Test the ScreenCapture class."""
    try:
        from client.screen_capture import ScreenCapture
        logger.info("✓ ScreenCapture class imported successfully")
        
        # Create instance
        screen_capture = ScreenCapture("test_client", None)
        logger.info("✓ ScreenCapture instance created")
        
        # Check capabilities
        capability_info = screen_capture.get_capability_info()
        logger.info(f"Capability info: {capability_info}")
        
        if capability_info.get('available', False):
            logger.info("✓ Screen capture is available")
            return True
        else:
            logger.error("❌ Screen capture is not available")
            logger.error(f"Capabilities: {capability_info.get('capabilities', {})}")
            logger.error(f"Permissions: {capability_info.get('permissions', {})}")
            logger.error(f"Dependencies: {capability_info.get('dependencies', {})}")
            return False
        
    except Exception as e:
        logger.error(f"❌ ScreenCapture test failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("Starting screen capture debug tests...")
    
    tests = [
        ("PyAutoGUI", test_pyautogui),
        ("PIL ImageGrab", test_pil_imagegrab),
        ("ScreenCapture Class", test_screen_capture_class)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        results[test_name] = test_func()
    
    logger.info("\n--- Test Results ---")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    if all(results.values()):
        logger.info("\n🎉 All tests passed! Screen capture should work.")
        return 0
    else:
        logger.error("\n💥 Some tests failed. Screen capture may not work properly.")
        return 1


if __name__ == "__main__":
    exit(main())