#!/usr/bin/env python3
"""
Debug script to test connection functionality with the new tabbed interface.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_connection():
    """Test connection with debug output."""
    from client.gui_manager import GUIManager
    
    print("🔧 Connection Debug Test")
    print("=" * 40)
    
    # Create GUI manager
    gui = GUIManager()
    
    # Test connection callbacks
    def debug_connect(username):
        print(f"✅ Connect callback called with username: {username}")
        print(f"📡 Attempting to connect to server...")
        # Simulate connection status updates
        gui.update_connection_status("connecting")
        gui.root.after(2000, lambda: gui.update_connection_status("connected"))
        gui.root.after(4000, lambda: print("🎉 Connection simulation complete!"))
    
    def debug_disconnect():
        print(f"❌ Disconnect callback called")
        gui.update_connection_status("disconnected")
    
    # Set up callbacks
    gui.set_connection_callbacks(debug_connect, debug_disconnect)
    
    print("🎯 Test Instructions:")
    print("1. Enter server address (e.g., localhost)")
    print("2. Enter username (e.g., TestUser)")
    print("3. Click '🔗 Connect' button")
    print("4. Watch console for debug output")
    print("5. Check header status indicator")
    print()
    print("Expected behavior:")
    print("✅ Console shows 'Connect callback called'")
    print("✅ Status changes to 'Connecting...' then 'Connected'")
    print("✅ Connect button becomes disabled")
    print("✅ Disconnect button becomes enabled")
    
    # Pre-fill for easy testing
    gui.server_entry.delete(0, 'end')
    gui.server_entry.insert(0, "localhost")
    gui.username_entry.delete(0, 'end')
    gui.username_entry.insert(0, "TestUser")
    
    # Start GUI
    gui.run()

if __name__ == "__main__":
    test_connection()