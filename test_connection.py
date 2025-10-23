#!/usr/bin/env python3
"""
Simple connection test script to verify the fixes work.
"""

import sys
import time
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """Test basic connection functionality."""
    print("Testing LAN Collaboration Suite connection...")
    
    # Create connection manager
    conn_mgr = ConnectionManager("localhost", 8080, 8081)
    
    try:
        # Test connection
        print("Attempting to connect...")
        success = conn_mgr.connect("TestUser")
        
        if success:
            print("✓ Connection successful!")
            print(f"Client ID: {conn_mgr.get_client_id()}")
            
            # Test sending a message
            print("Testing chat message...")
            success = conn_mgr.send_chat_message("Hello from test script!")
            if success:
                print("✓ Chat message sent successfully!")
            else:
                print("✗ Failed to send chat message")
            
            # Wait a moment
            time.sleep(2)
            
            # Disconnect
            print("Disconnecting...")
            conn_mgr.disconnect()
            print("✓ Disconnected successfully!")
            
        else:
            print("✗ Connection failed")
            return False
    
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n🎉 Connection test passed!")
        sys.exit(0)
    else:
        print("\n❌ Connection test failed!")
        sys.exit(1)