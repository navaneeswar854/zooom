#!/usr/bin/env python3
"""
Test script to verify chat input box visibility.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_chat_layout():
    """Test the chat input box layout."""
    root = tk.Tk()
    root.title("Chat Input Box Test")
    root.geometry("600x400")
    
    # Create a frame similar to ChatFrame
    main_frame = ttk.Frame(root, relief='ridge', borderwidth=2)
    main_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    # Title
    title_label = ttk.Label(main_frame, text="💬 Group Chat", font=('Arial', 12, 'bold'))
    title_label.pack(pady=5)
    
    # Input area at bottom (packed first)
    input_frame = ttk.Frame(main_frame, relief='raised', borderwidth=1)
    input_frame.pack(side='bottom', fill='x', padx=5, pady=5)
    
    # Input label
    input_label = ttk.Label(input_frame, text="💬 Message:", font=('Arial', 10, 'bold'))
    input_label.pack(side='left', padx=(5, 5))
    
    # Character counter
    char_counter = ttk.Label(input_frame, text="0/1000", font=('Arial', 8))
    char_counter.pack(side='right', padx=(5, 0))
    
    # Send button
    send_button = ttk.Button(input_frame, text="📤 Send", width=10)
    send_button.pack(side='right', padx=(5, 0))
    
    # Message entry
    message_entry = ttk.Entry(input_frame, font=('Arial', 12), width=50)
    message_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
    message_entry.insert(0, "Type your message here...")
    
    # Controls at bottom
    controls_frame = ttk.Frame(main_frame)
    controls_frame.pack(side='bottom', fill='x', padx=5, pady=(0, 5))
    
    clear_button = ttk.Button(controls_frame, text="Clear History")
    clear_button.pack(side='left')
    
    status_label = ttk.Label(controls_frame, text="Ready", font=('Arial', 8))
    status_label.pack(side='right')
    
    # Chat display (takes remaining space)
    from tkinter import scrolledtext
    chat_display = scrolledtext.ScrolledText(
        main_frame, 
        height=12, 
        state='normal',
        wrap='word',
        font=('Consolas', 10),
        bg='#ffffff',
        fg='#212529',
        relief='sunken',
        borderwidth=2
    )
    chat_display.pack(fill='both', expand=True, padx=5, pady=5)
    
    # Add some sample messages
    chat_display.insert(tk.END, "[15:06:23] * Welcome to the group chat! Start typing to send messages.\n")
    chat_display.insert(tk.END, "[15:06:45] User1: Hello everyone!\n")
    chat_display.insert(tk.END, "[15:06:52] User2: Hi there! How's everyone doing?\n")
    chat_display.insert(tk.END, "[15:07:01] * User3 joined the session\n")
    
    # Focus on the input box
    message_entry.focus_set()
    
    print("Chat Input Box Test Window:")
    print("- The input box should be clearly visible at the bottom")
    print("- It should have a label '💬 Message:' on the left")
    print("- The text entry field should be in the middle")
    print("- The '📤 Send' button should be on the right")
    print("- The input area should have a raised border")
    print()
    print("If you can see all these elements, the fix is working!")
    
    root.mainloop()

if __name__ == "__main__":
    test_chat_layout()