#!/usr/bin/env python3
"""
Simple script to connect to a LAN Collaboration Suite server on another laptop.
"""

import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from client.main_client import CollaborationClient
    from client.connection_manager import ConnectionManager
except ImportError as e:
    print(f"Error importing client modules: {e}")
    print("Make sure you have copied all the project files to this laptop.")
    input("Press Enter to exit...")
    sys.exit(1)


def get_server_ip():
    """Get server IP address from user."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Default to the known server IP
    default_ip = "10.36.87.57"
    
    server_ip = simpledialog.askstring(
        "Server Connection", 
        f"Enter the server IP address:\n(Default: {default_ip})",
        initialvalue=default_ip
    )
    
    root.destroy()
    
    if not server_ip:
        server_ip = default_ip
    
    return server_ip.strip()


def test_connection(server_ip):
    """Test connection to the server."""
    print(f"Testing connection to server at {server_ip}...")
    
    test_client = ConnectionManager(server_ip, 8080, 8081)
    
    try:
        success = test_client.connect("ConnectionTest")
        if success:
            print(f"✅ Successfully connected to server at {server_ip}!")
            participants = test_client.get_participants()
            print(f"Found {len(participants)} participants on the server.")
            test_client.disconnect()
            return True
        else:
            print(f"❌ Failed to connect to server at {server_ip}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    """Main function to connect to LAN server."""
    print("🌐 LAN Collaboration Suite - Client Connector")
    print("=" * 50)
    
    # Get server IP
    server_ip = get_server_ip()
    
    if not server_ip:
        print("No server IP provided. Exiting.")
        return
    
    print(f"Connecting to server: {server_ip}")
    
    # Test connection first
    if not test_connection(server_ip):
        print("\n❌ Connection test failed!")
        print("\nTroubleshooting tips:")
        print("1. Make sure the server laptop is running the server")
        print("2. Check that both laptops are on the same network")
        print("3. Verify the server IP address is correct")
        print("4. Check Windows Firewall settings on server laptop")
        input("\nPress Enter to exit...")
        return
    
    print("\n✅ Connection test successful!")
    print("Starting full client application...")
    
    try:
        # Create and run the full client
        client = CollaborationClient()
        
        # Override the default server host
        def custom_connect(username):
            client.current_username = username
            client.connection_manager = ConnectionManager(server_host=server_ip)
            
            # Setup all the callbacks as in the original
            client.connection_manager.register_status_callback(client._on_connection_status_changed)
            # ... (other callbacks would be set up here)
            
            # Connect in background thread
            import threading
            connect_thread = threading.Thread(
                target=lambda: client.connection_manager.connect(username),
                daemon=True
            )
            connect_thread.start()
        
        # Replace the connect method
        client._handle_connect = custom_connect
        
        # Run the client
        client.run()
        
    except Exception as e:
        print(f"Error starting client: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()