#!/usr/bin/env python3
"""
Minimal LAN connection test - uses only built-in Python modules.
"""

import socket
import json
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_connection(server_ip="10.36.87.57", port=8080):
    """Test basic TCP connection to server."""
    print(f"🌐 Testing basic connection to {server_ip}:{port}")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        
        # Connect
        print("Connecting...")
        sock.connect((server_ip, port))
        print("✅ TCP connection successful!")
        
        # Send a simple message (following the protocol)
        test_message = {
            "msg_type": "client_join",
            "sender_id": "minimal_test_client",
            "timestamp": time.time(),
            "data": {
                "username": "MinimalTestClient"
            }
        }
        
        message_data = json.dumps(test_message).encode('utf-8')
        message_length = len(message_data)
        
        # Send length first, then data (following the protocol)
        sock.send(message_length.to_bytes(4, byteorder='big'))
        sock.send(message_data)
        
        print("✅ Test message sent!")
        
        # Try to receive response
        print("Waiting for server response...")
        length_bytes = sock.recv(4)
        if length_bytes:
            response_length = int.from_bytes(length_bytes, byteorder='big')
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            print(f"✅ Received response: {response.get('msg_type', 'unknown')}")
            
            if response.get('msg_type') == 'welcome':
                client_id = response.get('data', {}).get('client_id', 'unknown')
                print(f"✅ Successfully joined server! Client ID: {client_id}")
                return True
        
        return False
        
    except socket.timeout:
        print("❌ Connection timeout - server may not be running")
        return False
    except ConnectionRefusedError:
        print("❌ Connection refused - check server IP and firewall")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    """Main test function."""
    print("🔍 Minimal LAN Connection Test")
    print("=" * 40)
    print("This test uses only built-in Python modules")
    print()
    
    # Get server IP
    server_ip = input("Enter server IP address (default: 10.36.87.57): ").strip()
    if not server_ip:
        server_ip = "10.36.87.57"
    
    # Test connection
    success = test_basic_connection(server_ip)
    
    if success:
        print("\n🎉 SUCCESS!")
        print("✅ Basic LAN connection is working")
        print("✅ Server is reachable and responding")
        print("✅ You can now run the full client application")
    else:
        print("\n❌ FAILED!")
        print("Check:")
        print("- Server is running on the other laptop")
        print("- Both laptops are on the same network")
        print("- Firewall allows connections")
        print("- IP address is correct")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()