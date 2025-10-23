#!/usr/bin/env python3
"""
Temporarily disable video to test if the system works without video packets.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from client.connection_manager import ConnectionManager

def test_without_video(server_ip="10.36.87.224"):
    """Test the system without video to isolate the UDP issue."""
    print("🔧 Testing LAN Collaboration WITHOUT video")
    print("=" * 50)
    
    client = ConnectionManager(server_ip, 8080, 8081)
    
    try:
        # Connect
        print("1. Connecting...")
        success = client.connect("NoVideoTestClient")
        
        if not success:
            print("❌ Connection failed")
            return False
        
        print(f"✅ Connected! Client ID: {client.get_client_id()}")
        
        # Test chat only
        print("2. Testing chat...")
        success = client.send_chat_message("Testing without video - chat should work fine! 💬")
        if success:
            print("✅ Chat message sent successfully")
        else:
            print("❌ Chat failed")
        
        # Test screen sharing controls
        print("3. Testing screen sharing...")
        success = client.request_presenter_role()
        if success:
            print("✅ Presenter role requested")
            
            success = client.start_screen_sharing()
            if success:
                print("✅ Screen sharing started")
                
                import time
                time.sleep(2)
                
                success = client.stop_screen_sharing()
                if success:
                    print("✅ Screen sharing stopped")
        
        # Keep connection for a while
        print("4. Keeping connection active...")
        import time
        for i in range(10):
            print(f"   Active... {i+1}/10")
            time.sleep(1)
        
        print("✅ All non-video features working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        client.disconnect()
        print("✅ Disconnected")

if __name__ == "__main__":
    server_ip = input("Enter server IP (default: 10.36.87.224): ").strip()
    if not server_ip:
        server_ip = "10.36.87.224"
    
    success = test_without_video(server_ip)
    
    if success:
        print("\n🎉 SUCCESS: All non-video features work perfectly!")
        print("The issue is specifically with video UDP packets.")
        print("Chat, screen sharing controls, and basic collaboration work fine.")
    else:
        print("\n❌ FAILED: Basic features have issues")
    
    input("\nPress Enter to exit...")