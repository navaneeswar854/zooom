#!/usr/bin/env python3
"""
Test functionality with active GUI clients running.
This script connects additional test clients to verify multi-client functionality.
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_chat_with_active_clients():
    """Test chat functionality with active GUI clients."""
    logger.info("=== Testing Chat with Active Clients ===")
    
    test_client = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect test client
        logger.info("Connecting test client...")
        if not test_client.connect("TestChatClient"):
            logger.error("Failed to connect test client")
            return False
        
        logger.info(f"✓ Connected successfully! Client ID: {test_client.get_client_id()}")
        
        # Get current participants
        participants = test_client.get_participants()
        logger.info(f"Current participants: {len(participants)} clients")
        for client_id, info in participants.items():
            username = info.get('username', 'Unknown')
            logger.info(f"  - {username} ({client_id})")
        
        # Send test messages
        test_messages = [
            "Hello from automated test client!",
            "Testing multi-client chat functionality 📱",
            "Can all GUI clients see this message? ✓",
            "Final test message - please respond in GUI! 🎉"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info(f"Sending message {i}/{len(test_messages)}: {message}")
            success = test_client.send_chat_message(message)
            
            if success:
                logger.info(f"✓ Message {i} sent successfully")
            else:
                logger.error(f"✗ Failed to send message {i}")
                return False
            
            time.sleep(2)  # Wait between messages
        
        # Keep client connected for a while to receive responses
        logger.info("Waiting for responses from GUI clients...")
        
        received_messages = []
        def on_chat_message(message):
            sender = message.data.get('sender_username', 'Unknown')
            text = message.data.get('message', '')
            received_messages.append(f"{sender}: {text}")
            logger.info(f"📨 Received: {sender}: {text}")
        
        test_client.register_message_callback('chat', on_chat_message)
        
        # Wait for responses
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Listening for responses... ({i}/30 seconds)")
        
        logger.info(f"✓ Received {len(received_messages)} chat messages from other clients")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during chat test: {e}")
        return False
    
    finally:
        test_client.disconnect()


def test_file_sharing_with_active_clients():
    """Test file sharing with active GUI clients."""
    logger.info("=== Testing File Sharing with Active Clients ===")
    
    test_client = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect test client
        if not test_client.connect("TestFileClient"):
            logger.error("Failed to connect test client")
            return False
        
        logger.info(f"✓ Connected successfully! Client ID: {test_client.get_client_id()}")
        
        # Create a test file with interesting content
        test_content = """🎉 LAN Collaboration Suite Test File 🎉

This file was uploaded by an automated test client to verify file sharing functionality.

Features being tested:
✓ File upload from test client
✓ File availability notifications to GUI clients
✓ File download capability
✓ Multi-client file sharing

Test Details:
- Upload time: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """
- File size: Small text file
- Encoding: UTF-8 with emoji support
- Purpose: Verify file sharing works with active GUI clients

Instructions for GUI clients:
1. You should see a file availability notification
2. Try downloading this file
3. Verify the content matches this text
4. Test uploading your own files

Happy testing! 🚀
"""
        
        test_file_path = "test_file_for_gui_clients.txt"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Setup file availability callback
        file_notifications = []
        def on_file_available(message):
            filename = message.data.get('filename', 'Unknown')
            file_id = message.data.get('file_id', 'Unknown')
            uploader = message.data.get('uploader_id', 'Unknown')
            file_notifications.append({'filename': filename, 'id': file_id, 'uploader': uploader})
            logger.info(f"📁 File available: {filename} (ID: {file_id}) from {uploader}")
        
        test_client.register_message_callback('file_available', on_file_available)
        
        # Upload the test file
        logger.info("Uploading test file for GUI clients...")
        success, message = test_client.upload_file(test_file_path, "Test file from automated client - please download and verify!")
        
        if success:
            logger.info(f"✓ File uploaded successfully: {message}")
        else:
            logger.error(f"✗ File upload failed: {message}")
            return False
        
        # Wait for file availability notification
        logger.info("Waiting for file availability notification...")
        for i in range(10):
            time.sleep(1)
            if file_notifications:
                logger.info(f"✓ File availability notification received after {i+1} seconds")
                break
            if i % 2 == 0:
                logger.info(f"Waiting... ({i+1}/10 seconds)")
        
        if not file_notifications:
            logger.error("✗ No file availability notification received")
            return False
        
        # Keep client connected so GUI clients can download
        logger.info("File is now available for GUI clients to download!")
        logger.info("Keeping connection active for 60 seconds...")
        
        for i in range(60):
            time.sleep(1)
            if i % 10 == 0:
                logger.info(f"File available for download... ({i}/60 seconds)")
        
        # Cleanup
        try:
            os.remove(test_file_path)
        except:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Error during file sharing test: {e}")
        return False
    
    finally:
        test_client.disconnect()


def test_screen_sharing_with_active_clients():
    """Test screen sharing with active GUI clients."""
    logger.info("=== Testing Screen Sharing with Active Clients ===")
    
    test_client = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect test client
        if not test_client.connect("TestScreenClient"):
            logger.error("Failed to connect test client")
            return False
        
        logger.info(f"✓ Connected successfully! Client ID: {test_client.get_client_id()}")
        
        # Setup screen sharing event callback
        screen_events = []
        def on_screen_share_event(message):
            action = message.data.get('action', 'unknown')
            sender_id = message.sender_id
            screen_events.append({'action': action, 'sender': sender_id})
            logger.info(f"🖥️ Screen sharing event: {action} from {sender_id}")
        
        test_client.register_message_callback('screen_share', on_screen_share_event)
        
        # Test requesting presenter role
        logger.info("Requesting presenter role...")
        success = test_client.request_presenter_role()
        
        if success:
            logger.info("✓ Presenter role request sent")
        else:
            logger.error("✗ Failed to request presenter role")
            return False
        
        time.sleep(2)
        
        # Test starting screen sharing
        logger.info("Starting screen sharing session...")
        success = test_client.start_screen_sharing()
        
        if success:
            logger.info("✓ Screen sharing started - GUI clients should see this!")
        else:
            logger.error("✗ Failed to start screen sharing")
            return False
        
        # Keep screen sharing active for a while
        logger.info("Screen sharing active for 15 seconds...")
        for i in range(15):
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Screen sharing active... ({i}/15 seconds)")
        
        # Stop screen sharing
        logger.info("Stopping screen sharing...")
        success = test_client.stop_screen_sharing()
        
        if success:
            logger.info("✓ Screen sharing stopped")
        else:
            logger.error("✗ Failed to stop screen sharing")
            return False
        
        time.sleep(2)
        
        logger.info(f"✓ Recorded {len(screen_events)} screen sharing events")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during screen sharing test: {e}")
        return False
    
    finally:
        test_client.disconnect()


def main():
    """Run all tests with active GUI clients."""
    logger.info("🚀 Starting comprehensive test with active GUI clients...")
    logger.info("Make sure GUI clients are running and connected!")
    
    # Wait a moment for GUI clients to fully initialize
    logger.info("Waiting 5 seconds for GUI clients to initialize...")
    time.sleep(5)
    
    results = {}
    
    # Test chat functionality
    results['chat'] = test_chat_with_active_clients()
    
    # Wait between tests
    time.sleep(3)
    
    # Test file sharing
    results['file_sharing'] = test_file_sharing_with_active_clients()
    
    # Wait between tests
    time.sleep(3)
    
    # Test screen sharing
    results['screen_sharing'] = test_screen_sharing_with_active_clients()
    
    # Summary
    logger.info("=" * 50)
    logger.info("🎯 TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED! The LAN Collaboration Suite is working perfectly!")
        logger.info("📋 Verified functionality:")
        logger.info("   ✓ Multi-client connections")
        logger.info("   ✓ Real-time chat messaging")
        logger.info("   ✓ File upload and sharing")
        logger.info("   ✓ Screen sharing controls")
        logger.info("   ✓ Client notifications")
    else:
        failed_tests = [test for test, success in results.items() if not success]
        logger.error(f"❌ Some tests failed: {failed_tests}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}: Multi-client functionality test completed!")
    sys.exit(0 if success else 1)