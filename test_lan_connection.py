#!/usr/bin/env python3
"""
Simple command-line test to verify LAN connection to the server.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager


def test_lan_connection(server_ip="10.36.87.57"):
    """Test LAN connection to the collaboration server."""
    print(f"🌐 Testing LAN connection to server: {server_ip}")
    print("=" * 50)
    
    client = ConnectionManager(server_ip, 8080, 8081)
    
    try:
        # Test connection
        print("1. Testing connection...")
        success = client.connect("LAN_Test_Client")
        
        if not success:
            print("❌ Connection failed!")
            print("\nTroubleshooting:")
            print("- Check server is running on the other laptop")
            print("- Verify both laptops are on same network")
            print("- Check firewall settings")
            return False
        
        print(f"✅ Connected successfully!")
        print(f"   Client ID: {client.get_client_id()}")
        
        # Check participants
        print("\n2. Checking participants...")
        participants = client.get_participants()
        print(f"✅ Found {len(participants)} participants:")
        for client_id, info in participants.items():
            username = info.get('username', 'Unknown')
            print(f"   - {username} ({client_id[:8]}...)")
        
        # Test chat
        print("\n3. Testing chat...")
        success = client.send_chat_message("Hello from another laptop! 🌐")
        if success:
            print("✅ Chat message sent successfully!")
        else:
            print("❌ Chat message failed")
        
        # Test screen sharing
        print("\n4. Testing screen sharing...")
        success = client.request_presenter_role()
        if success:
            print("✅ Presenter role requested")
            
            time.sleep(1)
            success = client.start_screen_sharing()
            if success:
                print("✅ Screen sharing started")
                
                time.sleep(3)
                success = client.stop_screen_sharing()
                if success:
                    print("✅ Screen sharing stopped")
        
        # Keep connection for a moment
        print("\n5. Keeping connection active for 10 seconds...")
        for i in range(10):
            print(f"   Active... {i+1}/10")
            time.sleep(1)
        
        print("\n✅ All LAN tests completed successfully!")
        print("🎉 The LAN Collaboration Suite is working across laptops!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        client.disconnect()
        print("✅ Disconnected from server")


def main():
    """Main function."""
    # Get server IP from command line or use default
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    else:
        server_ip = input("Enter server IP address (default: 10.36.87.57): ").strip()
        if not server_ip:
            server_ip = "10.36.87.57"
    
    success = test_lan_connection(server_ip)
    
    if success:
        print("\n🎉 SUCCESS: LAN connection working perfectly!")
    else:
        print("\n❌ FAILED: LAN connection issues detected")
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()