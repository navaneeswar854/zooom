#!/usr/bin/env python3
"""
Debug script to test screen manager functionality.
"""

import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_screen_manager_flow():
    """Test the exact flow that screen manager uses."""
    try:
        from client.screen_capture import ScreenCapture
        from client.screen_manager import ScreenManager
        
        logger.info("✓ Imported ScreenCapture and ScreenManager")
        
        # Create screen capture instance like screen manager does
        client_id = "test_client_123"
        connection_manager = None  # Screen manager might pass None in some cases
        
        logger.info("Creating ScreenCapture instance...")
        screen_capture = ScreenCapture(client_id, connection_manager)
        logger.info("✓ ScreenCapture instance created")
        
        # Test capability info like screen manager does
        logger.info("Getting capability info...")
        capability_info = screen_capture.get_capability_info()
        logger.info(f"Capability info: {capability_info}")
        
        # Check availability like screen manager does
        available = capability_info.get('available', False)
        logger.info(f"Available: {available}")
        
        if not available:
            error_msg = capability_info.get('error_message', 'Screen capture not available')
            logger.error(f"❌ Screen capture not available: {error_msg}")
            
            # Get setup instructions
            instructions = screen_capture.get_setup_instructions()
            if instructions:
                logger.info("Setup instructions:")
                for instruction in instructions:
                    logger.info(f"  - {instruction}")
            
            return False
        
        # Test start_capture like screen manager does
        logger.info("Testing start_capture...")
        success, message = screen_capture.start_capture()
        logger.info(f"Start capture result: success={success}, message='{message}'")
        
        if success:
            logger.info("✓ Screen capture started successfully")
            
            # Test stop_capture
            logger.info("Testing stop_capture...")
            screen_capture.stop_capture()
            logger.info("✓ Screen capture stopped")
            
            return True
        else:
            logger.error(f"❌ Failed to start screen capture: {message}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Screen manager flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_screen_manager():
    """Test creating a full screen manager instance."""
    try:
        from client.screen_manager import ScreenManager
        
        logger.info("Creating ScreenManager instance...")
        
        # Create like main client does
        client_id = "test_client_123"
        connection_manager = None  # Simplified for testing
        gui_manager = None  # Simplified for testing
        
        screen_manager = ScreenManager(client_id, connection_manager, gui_manager)
        logger.info("✓ ScreenManager instance created")
        
        # Test the exact method that's failing
        logger.info("Testing handle_screen_share_confirmed...")
        
        # This should trigger the capability check
        screen_manager.handle_screen_share_confirmed()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Full screen manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("Starting screen manager debug tests...")
    
    tests = [
        ("Screen Manager Flow", test_screen_manager_flow),
        ("Full Screen Manager", test_full_screen_manager)
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
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error("\n💥 Some tests failed.")
        return 1


if __name__ == "__main__":
    exit(main())