#!/usr/bin/env python3
"""
Test script to reproduce the exact screen sharing conditions from the logs.
"""

import logging
import threading
import time

# Configure logging to match the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_screen_manager_with_connection():
    """Test screen manager with a mock connection manager like in the real app."""
    try:
        from client.screen_manager import ScreenManager
        from client.connection_manager import ConnectionManager
        
        logger.info("Creating mock connection manager...")
        
        # Create a mock connection manager (like in the real app)
        connection_manager = ConnectionManager()
        
        logger.info("Creating screen manager with connection manager...")
        client_id = "9cd825e8-37a9-4f8b-b01d-aa7c5575e73e"  # Same as in logs
        screen_manager = ScreenManager(client_id, connection_manager, None)
        
        logger.info("Screen manager created successfully")
        
        # Simulate the exact flow from the logs
        logger.info("Simulating presenter role granted...")
        screen_manager.handle_presenter_granted()
        
        # Wait a bit like in the real app
        time.sleep(0.1)
        
        logger.info("Simulating screen share confirmed...")
        screen_manager.handle_screen_share_confirmed()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screen_capture_in_thread():
    """Test screen capture in a separate thread like the real app."""
    def capture_test():
        try:
            from client.screen_capture import ScreenCapture
            
            logger.info("Creating screen capture in thread...")
            client_id = "9cd825e8-37a9-4f8b-b01d-aa7c5575e73e"
            screen_capture = ScreenCapture(client_id, None)
            
            logger.info("Getting capability info in thread...")
            capability_info = screen_capture.get_capability_info()
            logger.info(f"Thread capability info: {capability_info}")
            
            available = capability_info.get('available', False)
            logger.info(f"Thread available: {available}")
            
            if available:
                logger.info("Testing start_capture in thread...")
                success, message = screen_capture.start_capture()
                logger.info(f"Thread start_capture: success={success}, message='{message}'")
                
                if success:
                    time.sleep(1)  # Capture for a bit
                    screen_capture.stop_capture()
                    logger.info("Thread capture stopped")
                
                return success
            else:
                logger.error("Screen capture not available in thread")
                return False
                
        except Exception as e:
            logger.error(f"Thread test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run in thread
    result = [False]
    
    def thread_wrapper():
        result[0] = capture_test()
    
    thread = threading.Thread(target=thread_wrapper, daemon=True)
    thread.start()
    thread.join(timeout=10)
    
    return result[0]


def test_multiple_screen_captures():
    """Test creating multiple screen capture instances like in the real app."""
    try:
        from client.screen_capture import ScreenCapture
        
        logger.info("Creating multiple screen capture instances...")
        
        instances = []
        for i in range(3):
            client_id = f"test_client_{i}"
            instance = ScreenCapture(client_id, None)
            instances.append(instance)
            logger.info(f"Created instance {i}")
            
            # Test each instance
            capability_info = instance.get_capability_info()
            available = capability_info.get('available', False)
            logger.info(f"Instance {i} available: {available}")
            
            if not available:
                logger.error(f"Instance {i} not available: {capability_info}")
                return False
        
        logger.info("All instances created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Multiple instances test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("Starting real conditions screen sharing tests...")
    
    tests = [
        ("Screen Manager with Connection", test_screen_manager_with_connection),
        ("Screen Capture in Thread", test_screen_capture_in_thread),
        ("Multiple Screen Captures", test_multiple_screen_captures)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
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