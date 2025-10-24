#!/usr/bin/env python3
"""
Complete test to verify screen sharing functionality is working.
"""

import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_complete_screen_sharing_flow():
    """Test the complete screen sharing flow that should work in the real app."""
    try:
        from client.screen_manager import ScreenManager
        from client.connection_manager import ConnectionManager
        
        logger.info("=== Testing Complete Screen Sharing Flow ===")
        
        # Step 1: Create components like in real app
        logger.info("Step 1: Creating components...")
        client_id = "test_client_123"
        connection_manager = ConnectionManager()
        screen_manager = ScreenManager(client_id, connection_manager, None)
        logger.info("✓ Components created successfully")
        
        # Step 2: Test capability check
        logger.info("Step 2: Testing capability check...")
        capability_info = screen_manager.screen_capture.get_capability_info()
        available = capability_info.get('available', False)
        logger.info(f"Screen capture available: {available}")
        
        if not available:
            logger.error("❌ Screen capture not available")
            logger.error(f"Capabilities: {capability_info.get('capabilities', {})}")
            logger.error(f"Permissions: {capability_info.get('permissions', {})}")
            return False
        
        logger.info("✓ Screen capture is available")
        
        # Step 3: Test presenter role flow
        logger.info("Step 3: Testing presenter role flow...")
        screen_manager.handle_presenter_granted()
        logger.info("✓ Presenter role granted")
        
        # Step 4: Test screen share confirmation (the critical part)
        logger.info("Step 4: Testing screen share confirmation...")
        screen_manager.handle_screen_share_confirmed()
        
        # Check if sharing started
        if screen_manager.is_sharing:
            logger.info("✓ Screen sharing started successfully!")
            
            # Let it run for a moment
            time.sleep(2)
            
            # Stop sharing
            screen_manager.stop_screen_sharing()
            logger.info("✓ Screen sharing stopped successfully")
            
            return True
        else:
            logger.error("❌ Screen sharing did not start")
            return False
        
    except Exception as e:
        logger.error(f"❌ Complete flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_handling():
    """Test that the message handling fixes are working."""
    try:
        from common.messages import MessageFactory, MessageType, MessageValidator
        
        logger.info("=== Testing Message Handling Fixes ===")
        
        # Test screen share confirmed message
        confirm_message = MessageFactory.create_tcp_message(
            msg_type=MessageType.SCREEN_SHARE_CONFIRMED.value,
            sender_id='server',
            data={'status': 'started'}
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(confirm_message)
        if not is_valid:
            logger.error(f"❌ SCREEN_SHARE_CONFIRMED validation failed: {error_msg}")
            return False
        
        logger.info("✓ SCREEN_SHARE_CONFIRMED message validation passed")
        
        # Test screen share error message
        error_message = MessageFactory.create_tcp_message(
            msg_type=MessageType.SCREEN_SHARE_ERROR.value,
            sender_id='server',
            data={'error': 'Test error message'}
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(error_message)
        if not is_valid:
            logger.error(f"❌ SCREEN_SHARE_ERROR validation failed: {error_msg}")
            return False
        
        logger.info("✓ SCREEN_SHARE_ERROR message validation passed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Message handling test failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("🚀 Starting complete screen sharing verification...")
    
    tests = [
        ("Message Handling Fixes", test_message_handling),
        ("Complete Screen Sharing Flow", test_complete_screen_sharing_flow)
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    logger.info("\n=== FINAL RESULTS ===")
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("Screen sharing should now work correctly in the application!")
        logger.info("\nFixes implemented:")
        logger.info("✓ Added missing SCREEN_SHARE_CONFIRMED and SCREEN_SHARE_ERROR message types")
        logger.info("✓ Updated server to use proper MessageType enum values")
        logger.info("✓ Fixed client callback registration")
        logger.info("✓ Added message validation for new types")
        logger.info("✓ Fixed screen capture capability checking")
        logger.info("✓ Enhanced error handling and logging")
        return 0
    else:
        logger.error("\n💥 SOME TESTS FAILED!")
        logger.error("There may still be issues with screen sharing.")
        return 1


if __name__ == "__main__":
    exit(main())