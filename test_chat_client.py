#!/usr/bin/env python3
"""
Simple test client to demonstrate the enhanced chat functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client.main_client import CollaborationClient

def main():
    """Test the enhanced chat client."""
    print("Starting enhanced chat test client...")
    print("The chat interface now includes:")
    print("- 💬 Enhanced chat title with emoji")
    print("- Larger, more readable chat display")
    print("- Placeholder text in message input")
    print("- Better visual styling")
    print("- Welcome message on startup")
    print("- Enhanced send button with emoji")
    print()
    
    try:
        client = CollaborationClient()
        client.run()
    except Exception as e:
        print(f"Error starting client: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()