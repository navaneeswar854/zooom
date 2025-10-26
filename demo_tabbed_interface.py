#!/usr/bin/env python3
"""
Demo of the new tabbed interface with separated modules.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def demo_tabbed_interface():
    """Demo the new tabbed interface."""
    from client.gui_manager import GUIManager
    from datetime import datetime
    
    # Create GUI manager
    gui = GUIManager()
    
    # Add some demo content to chat
    if gui.chat_frame:
        gui.chat_frame.add_system_message("🎉 Welcome to the new tabbed interface!")
        gui.chat_frame.add_message("Alice", "This new interface looks amazing!", datetime.now(), False)
        gui.chat_frame.add_message("Bob", "I love how everything is organized in tabs!", datetime.now(), False)
        gui.chat_frame.add_system_message("Charlie joined the session")
        
        # Demo callback
        def demo_send_message(message):
            gui.chat_frame.add_message("You", message, datetime.now(), True)
            print(f"Demo: Sending message: {message}")
        
        gui.chat_frame.set_message_callback(demo_send_message)
    
    # Add demo files to file sharing
    if gui.file_transfer_frame:
        gui.file_transfer_frame.add_shared_file("file1", "presentation.pdf", 2048000, "Alice")
        gui.file_transfer_frame.add_shared_file("file2", "project_code.zip", 5120000, "Bob")
        gui.file_transfer_frame.add_shared_file("file3", "meeting_notes.docx", 512000, "Charlie")
    
    print("🚀 Modern Tabbed Interface Features:")
    print("=" * 50)
    print("✅ 💬 Chat Tab - Real-time messaging with modern UI")
    print("✅ 📹 Video Conference Tab - Video calls and audio controls")
    print("✅ 🖥️ Screen Share Tab - Screen sharing and presentation")
    print("✅ 📁 File Sharing Tab - Upload and download files")
    print()
    print("🎨 Design Features:")
    print("✅ Modern dark header with connection controls")
    print("✅ Clean tabbed interface for easy navigation")
    print("✅ Professional color scheme and typography")
    print("✅ Responsive layout that adapts to window size")
    print("✅ Status bar with real-time updates")
    print("✅ Intuitive icons and visual feedback")
    print()
    print("🔧 Try these features:")
    print("1. Switch between tabs to see different modules")
    print("2. Type messages in the Chat tab")
    print("3. Check out the file sharing interface")
    print("4. Notice the connection status in the header")
    print("5. Resize the window to see responsive design")
    
    # Start the GUI
    gui.run()

if __name__ == "__main__":
    demo_tabbed_interface()