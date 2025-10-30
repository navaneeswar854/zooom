#!/usr/bin/env python3
"""
Test to verify clean logging without duplicate messages.
"""

import sys
import os
import logging
import io

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.main_client import CollaborationClient
from common.messages import TCPMessage

def test_logging_cleanup():
    """Test that video disable/enable produces clean logging."""
    
    print("🧪 Testing Logging Cleanup")
    print("=" * 40)
    
    # Capture log output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    # Get the root logger and add our handler
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    try:
        # Create a client (without connecting)
        client = CollaborationClient()
        client.video_enabled = True  # Start with video enabled
        
        print("1. Testing local video disable...")
        
        # Clear log capture
        log_capture.seek(0)
        log_capture.truncate(0)
        
        # Simulate video disable
        client._handle_video_toggle(False)
        
        # Get log output
        log_output = log_capture.getvalue()
        log_lines = [line.strip() for line in log_output.split('\n') if line.strip()]
        
        # Filter for video-related messages
        video_messages = [line for line in log_lines if 'video' in line.lower() or 'blank' in line.lower()]
        
        print(f"   Log messages for video disable: {len(video_messages)}")
        for msg in video_messages:
            print(f"   - {msg}")
        
        # Should have minimal messages
        if len(video_messages) <= 2:  # Allow for reasonable logging
            print("   ✅ Clean logging for video disable")
        else:
            print("   ❌ Too many log messages for video disable")
            return False
        
        print("\n2. Testing local video enable...")
        
        # Clear log capture
        log_capture.seek(0)
        log_capture.truncate(0)
        
        # Simulate video enable
        client._handle_video_toggle(True)
        
        # Get log output
        log_output = log_capture.getvalue()
        log_lines = [line.strip() for line in log_output.split('\n') if line.strip()]
        
        # Filter for video-related messages
        video_messages = [line for line in log_lines if 'video' in line.lower() or 'blank' in line.lower()]
        
        print(f"   Log messages for video enable: {len(video_messages)}")
        for msg in video_messages:
            print(f"   - {msg}")
        
        # Should have minimal messages
        if len(video_messages) <= 2:  # Allow for reasonable logging
            print("   ✅ Clean logging for video enable")
        else:
            print("   ❌ Too many log messages for video enable")
            return False
        
        print("\n3. Testing participant status update...")
        
        # Clear log capture
        log_capture.seek(0)
        log_capture.truncate(0)
        
        # Create a mock connection manager
        class MockConnectionManager:
            def get_participants(self):
                return {
                    'test_client_123': {
                        'username': 'TestUser',
                        'video_enabled': False,
                        'audio_enabled': True
                    }
                }
            
            def get_client_id(self):
                return 'local_client_456'
        
        client.connection_manager = MockConnectionManager()
        
        # Create a participant status update message
        status_message = TCPMessage(
            msg_type='participant_status_update',
            sender_id='server',
            data={
                'client_id': 'test_client_123',
                'video_enabled': False,
                'audio_enabled': True
            }
        )
        
        # Simulate participant status update
        client._on_participant_status_update(status_message)
        
        # Get log output
        log_output = log_capture.getvalue()
        log_lines = [line.strip() for line in log_output.split('\n') if line.strip()]
        
        # Filter for video-related messages
        video_messages = [line for line in log_lines if 'video' in line.lower() or 'blank' in line.lower()]
        
        print(f"   Log messages for participant update: {len(video_messages)}")
        for msg in video_messages:
            print(f"   - {msg}")
        
        # Should have minimal messages
        if len(video_messages) <= 1:  # Should be very minimal for participant updates
            print("   ✅ Clean logging for participant status update")
        else:
            print("   ❌ Too many log messages for participant status update")
            return False
        
        print("\n✅ All logging tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Remove our handler
        root_logger.removeHandler(handler)

if __name__ == "__main__":
    print("🔍 Testing Video Logging Cleanup")
    print("Checking for duplicate or excessive log messages...")
    print()
    
    success = test_logging_cleanup()
    
    if success:
        print("\n🎉 Logging cleanup successful!")
        print("Video disable/enable now produces clean, minimal log output.")
    else:
        print("\n❌ Logging cleanup needed!")
        print("There are still duplicate or excessive log messages.")
    
    sys.exit(0 if success else 1)