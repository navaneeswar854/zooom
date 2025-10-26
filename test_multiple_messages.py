#!/usr/bin/env python3
"""
Test script to verify multiple message sending works correctly.
"""

import tkinter as tk
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_multiple_messages():
    """Test sending multiple messages."""
    root = tk.Tk()
    root.title("Multiple Messages Test")
    root.geometry("600x500")
    
    # Import and create the ChatFrame
    from client.gui_manager import ChatFrame
    
    # Create the chat frame
    chat_frame = ChatFrame(root)
    chat_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Message counter
    message_count = [0]
    
    # Test callback
    def test_send_message(message):
        message_count[0] += 1
        from datetime import datetime
        chat_frame.add_message(f"User", f"Message #{message_count[0]}: {message}", datetime.now(), True)
        print(f"✅ Sent message #{message_count[0]}: {message}")
        
        # Check if placeholder is correctly handled
        if chat_frame.placeholder_active:
            print(f"❌ ERROR: Placeholder is active after sending message #{message_count[0]}")
        else:
            print(f"✅ OK: Placeholder correctly inactive after message #{message_count[0]}")
    
    chat_frame.set_message_callback(test_send_message)
    
    # Add instructions
    from datetime import datetime
    chat_frame.add_system_message("🧪 Testing multiple message sending...")
    chat_frame.add_system_message("Type messages and press Enter to test")
    chat_frame.add_system_message("You should be able to send multiple messages without errors")
    
    # Focus on input
    chat_frame.message_entry.focus_set()
    
    print("🧪 Multiple Messages Test")
    print("=" * 40)
    print("1. Type a message and press Enter")
    print("2. Type another message and press Enter")
    print("3. Repeat - you should NOT get 'Please enter a message' error")
    print("4. Check console for test results")
    print()
    print("Expected behavior:")
    print("✅ First message sends successfully")
    print("✅ Input box stays empty and ready for next message")
    print("✅ Second message sends without errors")
    print("✅ Can continue sending messages indefinitely")
    print()
    
    root.mainloop()

if __name__ == "__main__":
    test_multiple_messages()