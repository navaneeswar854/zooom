#!/usr/bin/env python3
"""
Demo of the modern chat interface with beautiful GUI.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def demo_modern_chat():
    """Demo the modern chat interface."""
    root = tk.Tk()
    root.title("Modern Chat Interface Demo")
    root.geometry("800x600")
    root.configure(bg='#ecf0f1')
    
    # Create main container
    main_frame = tk.Frame(root, bg='#ecf0f1')
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Import and create the ChatFrame
    from client.gui_manager import ChatFrame
    
    # Create the modern chat frame
    chat_frame = ChatFrame(main_frame)
    chat_frame.pack(fill='both', expand=True)
    
    # Add some demo messages
    from datetime import datetime
    
    chat_frame.add_system_message("💬 Welcome! Start chatting with your team...")
    chat_frame.add_message("Alice", "Hey everyone! How's the project going?", datetime.now(), False)
    chat_frame.add_message("Bob", "Great! Just finished the UI improvements.", datetime.now(), False)
    chat_frame.add_message("You", "The new chat interface looks amazing! 🎉", datetime.now(), True)
    chat_frame.add_system_message("Charlie joined the session")
    chat_frame.add_message("Charlie", "Wow, this interface is so clean and modern!", datetime.now(), False)
    
    # Demo callback
    def demo_send_message(message):
        chat_frame.add_message("You", message, datetime.now(), True)
        print(f"Demo: Sending message: {message}")
    
    chat_frame.set_message_callback(demo_send_message)
    
    # Focus on input
    chat_frame.message_entry.focus_set()
    
    # Add title
    title_label = tk.Label(
        main_frame,
        text="🚀 Modern Chat Interface Demo",
        font=('Segoe UI', 16, 'bold'),
        fg='#2c3e50',
        bg='#ecf0f1'
    )
    title_label.pack(side='top', pady=(0, 10))
    
    print("🎨 Modern Chat Interface Features:")
    print("✅ Beautiful modern design with Segoe UI font")
    print("✅ Prominent input area at the bottom")
    print("✅ Placeholder text with focus effects")
    print("✅ Modern color scheme (blues, grays)")
    print("✅ Hover effects on buttons")
    print("✅ Character counter with color coding")
    print("✅ Clean, flat design with subtle borders")
    print("✅ Emoji support in messages and buttons")
    print("✅ Responsive layout that adapts to window size")
    print("✅ Professional status indicators")
    print()
    print("💬 Try typing in the input box and pressing Enter!")
    
    root.mainloop()

if __name__ == "__main__":
    demo_modern_chat()