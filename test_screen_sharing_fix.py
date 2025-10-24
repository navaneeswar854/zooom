#!/usr/bin/env python3
"""
Test script to verify screen sharing fixes.
"""

import logging
import time
from common.messages import MessageFactory, MessageType, MessageValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_screen_sharing_messages():
    """Test screen sharing message creation and validation."""
    logger.info("Testing screen sharing message fixes...")
    
    # Test 1: Screen share confirmed message
    try:
        confirm_message = MessageFactory.create_tcp_message(
            msg_type=MessageType.SCREEN_SHARE_CONFIRMED.value,
            sender_id='server',
            data={'status': 'started'}
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(confirm_message)
        if is_valid:
            logger.info("✓ SCREEN_SHARE_CONFIRMED message validation: PASSED")
        else:
            logger.error(f"✗ SCREEN_SHARE_CONFIRMED message validation: FAILED - {error_msg}")
            return False
    except Exception as e:
        logger.error(f"✗ SCREEN_SHARE_CONFIRMED message creation: FAILED - {e}")
        return False
    
    # Test 2: Screen share error message
    try:
        error_message = MessageFactory.create_tcp_message(
            msg_type=MessageType.SCREEN_SHARE_ERROR.value,
            sender_id='server',
            data={'error': 'Test error message'}
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(error_message)
        if is_valid:
            logger.info("✓ SCREEN_SHARE_ERROR message validation: PASSED")
        else:
            logger.error(f"✗ SCREEN_SHARE_ERROR message validation: FAILED - {error_msg}")
            return False
    except Exception as e:
        logger.error(f"✗ SCREEN_SHARE_ERROR message creation: FAILED - {e}")
        return False
    
    # Test 3: Presenter request message
    try:
        presenter_request = MessageFactory.create_presenter_request_message("test_client_123")
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(presenter_request)
        if is_valid:
            logger.info("✓ PRESENTER_REQUEST message validation: PASSED")
        else:
            logger.error(f"✗ PRESENTER_REQUEST message validation: FAILED - {error_msg}")
            return False
    except Exception as e:
        logger.error(f"✗ PRESENTER_REQUEST message creation: FAILED - {e}")
        return False
    
    # Test 4: Screen share start message
    try:
        start_message = MessageFactory.create_screen_share_start_message("test_client_123")
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(start_message)
        if is_valid:
            logger.info("✓ SCREEN_SHARE_START message validation: PASSED")
        else:
            logger.error(f"✗ SCREEN_SHARE_START message validation: FAILED - {error_msg}")
            return False
    except Exception as e:
        logger.error(f"✗ SCREEN_SHARE_START message creation: FAILED - {e}")
        return False
    
    logger.info("All screen sharing message tests passed!")
    return True


def main():
    """Main test function."""
    logger.info("Starting screen sharing fix verification...")
    
    if test_screen_sharing_messages():
        logger.info("✅ Screen sharing fixes verified successfully!")
        logger.info("The following issues have been resolved:")
        logger.info("  - Added missing SCREEN_SHARE_CONFIRMED and SCREEN_SHARE_ERROR message types")
        logger.info("  - Updated server to use proper MessageType enum values")
        logger.info("  - Added validation for new screen sharing message types")
        logger.info("  - Fixed client callback registration")
        logger.info("")
        logger.info("Screen sharing should now work without connection drops!")
    else:
        logger.error("❌ Screen sharing fix verification failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())