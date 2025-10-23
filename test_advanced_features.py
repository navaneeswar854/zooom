#!/usr/bin/env python3
"""
Test advanced features like screen sharing, file transfer, and media streaming.
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


def test_file_transfer():
    """Test file upload and download functionality."""
    logger.info("=== Testing File Transfer ===")
    
    # Create test clients
    uploader = ConnectionManager("localhost", 8080, 8081)
    downloader = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect both clients
        logger.info("Connecting uploader client...")
        if not uploader.connect("FileUploader"):
            logger.error("Failed to connect uploader")
            return False
        
        logger.info("Connecting downloader client...")
        if not downloader.connect("FileDownloader"):
            logger.error("Failed to connect downloader")
            return False
        
        # Create a test file
        test_file_content = "This is a comprehensive test file for the LAN Collaboration Suite.\n"
        test_file_content += "Testing file transfer functionality with multiple lines.\n"
        test_file_content += "Line 3: Special characters: !@#$%^&*()\n"
        test_file_content += "Line 4: Unicode: 🎉 ✓ ❌ 📁 💻\n"
        
        test_file_path = "advanced_test_file.txt"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_file_content)
        
        # Setup file availability callback for downloader
        available_files = []
        def on_file_available(message):
            file_id = message.data.get('file_id')
            filename = message.data.get('filename')
            available_files.append({'id': file_id, 'name': filename})
            logger.info(f"File available for download: {filename} (ID: {file_id})")
        
        downloader.register_message_callback('file_available', on_file_available)
        
        # Upload file
        logger.info("Uploading test file...")
        success, message = uploader.upload_file(test_file_path, "Advanced test file with special content")
        
        if success:
            logger.info(f"✓ File upload successful: {message}")
        else:
            logger.error(f"✗ File upload failed: {message}")
            return False
        
        # Wait for file availability notification
        time.sleep(3)
        
        # Check if downloader received file notification
        if available_files:
            file_info = available_files[0]
            logger.info(f"✓ File availability notification received: {file_info['name']}")
            
            # Test file download
            logger.info("Testing file download...")
            download_success = downloader.request_file_download(file_info['id'])
            
            if download_success:
                logger.info("✓ File download request sent successfully")
                time.sleep(3)  # Wait for download to complete
                
                # Check if file was downloaded
                download_path = os.path.join("downloads", file_info['name'])
                if os.path.exists(download_path):
                    logger.info(f"✓ File downloaded successfully to: {download_path}")
                    
                    # Verify file content
                    with open(download_path, 'r', encoding='utf-8') as f:
                        downloaded_content = f.read()
                    
                    if downloaded_content == test_file_content:
                        logger.info("✓ File content verification successful")
                    else:
                        logger.error("✗ File content verification failed")
                        return False
                else:
                    logger.error("✗ Downloaded file not found")
                    return False
            else:
                logger.error("✗ File download request failed")
                return False
        else:
            logger.error("✗ File availability notification not received")
            return False
        
        # Cleanup
        try:
            os.remove(test_file_path)
            if os.path.exists(download_path):
                os.remove(download_path)
        except:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Error during file transfer test: {e}")
        return False
    
    finally:
        uploader.disconnect()
        downloader.disconnect()


def test_screen_sharing():
    """Test screen sharing functionality."""
    logger.info("=== Testing Screen Sharing ===")
    
    presenter = ConnectionManager("localhost", 8080, 8081)
    viewer = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect both clients
        logger.info("Connecting presenter client...")
        if not presenter.connect("ScreenPresenter"):
            logger.error("Failed to connect presenter")
            return False
        
        logger.info("Connecting viewer client...")
        if not viewer.connect("ScreenViewer"):
            logger.error("Failed to connect viewer")
            return False
        
        # Setup screen sharing callbacks
        screen_share_events = []
        def on_screen_share_message(message):
            action = message.data.get('action', 'unknown')
            screen_share_events.append(action)
            logger.info(f"Screen sharing event: {action}")
        
        viewer.register_message_callback('screen_share', on_screen_share_message)
        
        # Test requesting presenter role
        logger.info("Requesting presenter role...")
        success = presenter.request_presenter_role()
        
        if success:
            logger.info("✓ Presenter role request sent successfully")
        else:
            logger.error("✗ Failed to request presenter role")
            return False
        
        time.sleep(1)
        
        # Test starting screen sharing
        logger.info("Starting screen sharing...")
        success = presenter.start_screen_sharing()
        
        if success:
            logger.info("✓ Screen sharing start request sent successfully")
        else:
            logger.error("✗ Failed to start screen sharing")
            return False
        
        time.sleep(2)
        
        # Test stopping screen sharing
        logger.info("Stopping screen sharing...")
        success = presenter.stop_screen_sharing()
        
        if success:
            logger.info("✓ Screen sharing stop request sent successfully")
        else:
            logger.error("✗ Failed to stop screen sharing")
            return False
        
        time.sleep(1)
        
        # Check if viewer received screen sharing events
        if screen_share_events:
            logger.info(f"✓ Screen sharing events received: {screen_share_events}")
        else:
            logger.warning("⚠ No screen sharing events received by viewer")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during screen sharing test: {e}")
        return False
    
    finally:
        presenter.disconnect()
        viewer.disconnect()


def test_media_status_updates():
    """Test media status updates (audio/video enable/disable)."""
    logger.info("=== Testing Media Status Updates ===")
    
    client1 = ConnectionManager("localhost", 8080, 8081)
    client2 = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Connect both clients
        if not client1.connect("MediaClient1"):
            logger.error("Failed to connect client1")
            return False
        
        if not client2.connect("MediaClient2"):
            logger.error("Failed to connect client2")
            return False
        
        # Setup status update callback
        status_updates = []
        def on_status_update(message):
            client_id = message.data.get('client_id')
            video_enabled = message.data.get('video_enabled')
            audio_enabled = message.data.get('audio_enabled')
            status_updates.append({
                'client_id': client_id,
                'video': video_enabled,
                'audio': audio_enabled
            })
            logger.info(f"Media status update: Client {client_id} - Video: {video_enabled}, Audio: {audio_enabled}")
        
        client2.register_message_callback('participant_status_update', on_status_update)
        
        # Test media status updates
        logger.info("Testing media status updates...")
        
        # Enable video and audio
        success = client1.update_media_status(video_enabled=True, audio_enabled=True)
        if success:
            logger.info("✓ Media status update (video=True, audio=True) sent successfully")
        else:
            logger.error("✗ Failed to send media status update")
            return False
        
        time.sleep(1)
        
        # Disable video, keep audio
        success = client1.update_media_status(video_enabled=False, audio_enabled=True)
        if success:
            logger.info("✓ Media status update (video=False, audio=True) sent successfully")
        else:
            logger.error("✗ Failed to send media status update")
            return False
        
        time.sleep(1)
        
        # Check if client2 received status updates
        if status_updates:
            logger.info(f"✓ Received {len(status_updates)} media status updates")
            for update in status_updates:
                logger.info(f"  - Client {update['client_id']}: Video={update['video']}, Audio={update['audio']}")
        else:
            logger.warning("⚠ No media status updates received")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during media status test: {e}")
        return False
    
    finally:
        client1.disconnect()
        client2.disconnect()


def main():
    """Run all advanced feature tests."""
    logger.info("Starting advanced features test suite...")
    
    results = {}
    
    # Test file transfer
    results['file_transfer'] = test_file_transfer()
    
    # Test screen sharing
    results['screen_sharing'] = test_screen_sharing()
    
    # Test media status updates
    results['media_status'] = test_media_status_updates()
    
    # Summary
    logger.info("=== ADVANCED FEATURES TEST SUMMARY ===")
    for feature, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{feature}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("🎉 All advanced features tests passed!")
        return True
    else:
        failed_tests = [feature for feature, success in results.items() if not success]
        logger.error(f"❌ Some tests failed: {failed_tests}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)