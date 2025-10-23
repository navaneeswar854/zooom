#!/usr/bin/env python3
"""
Debug test for file notification system.
"""

import sys
import time
import logging
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_file_notification_debug():
    """Debug file notification system with detailed logging."""
    logger.info("=== File Notification Debug Test ===")
    
    uploader = ConnectionManager("localhost", 8080, 8081)
    downloader = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect clients
        logger.info("Connecting clients...")
        if not uploader.connect("DebugUploader"):
            logger.error("Failed to connect uploader")
            return False
        
        if not downloader.connect("DebugDownloader"):
            logger.error("Failed to connect downloader")
            return False
        
        # Setup detailed callback for downloader
        notifications_received = []
        
        def on_file_available(message):
            logger.info(f"FILE AVAILABLE CALLBACK TRIGGERED!")
            logger.info(f"Message type: {message.msg_type}")
            logger.info(f"Message data: {message.data}")
            notifications_received.append(message.data)
        
        def on_any_message(message):
            logger.debug(f"Received message: {message.msg_type}")
        
        # Register callbacks
        downloader.register_message_callback('file_available', on_file_available)
        
        # Create a small test file
        test_content = "Small test file for debugging\n"
        test_file = "debug_test.txt"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        logger.info("Uploading file...")
        success, message = uploader.upload_file(test_file, "Debug test file")
        
        if success:
            logger.info(f"✓ Upload successful: {message}")
        else:
            logger.error(f"✗ Upload failed: {message}")
            return False
        
        # Wait longer and check multiple times
        for i in range(15):
            logger.info(f"Waiting for notification... ({i+1}/15)")
            time.sleep(0.5)  # Check more frequently
            
            if notifications_received:
                logger.info(f"✓ Notification received after {(i+1)*0.5} seconds!")
                break
        
        if notifications_received:
            logger.info(f"✓ File notification received: {notifications_received[0]}")
            return True
        else:
            logger.error("✗ No file notification received after 7.5 seconds")
            return False
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            os.remove(test_file)
        except:
            pass
        
        uploader.disconnect()
        downloader.disconnect()


if __name__ == "__main__":
    success = test_file_notification_debug()
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")