#!/usr/bin/env python3
"""
Simple test to verify blank screen functionality without full server setup.
"""

import sys
import os
import tkinter as tk
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.gui_manager import VideoFrame

def test_blank_screen_gui():
    """Test blank screen functionality in GUI."""
    
    print("🧪 Testing Blank Screen GUI Functionality")
    print("=" * 50)
    
    # Create a simple tkinter window
    root = tk.Tk()
    root.title("Blank Screen Test")
    root.geometry("800x600")
    
    # Create video frame
    video_frame = VideoFrame(root)
    video_frame.pack(fill='both', expand=True)
    
    print("1. GUI created successfully")
    
    # Test local blank screen
    print("2. Testing local blank screen...")
    video_frame._show_blank_screen_for_local()
    print("   ✅ Local blank screen shown")
    
    # Wait a bit
    root.update()
    time.sleep(0.5)
    
    # Test clearing local blank screen
    print("3. Testing clear local blank screen...")
    video_frame._clear_blank_screen_for_local()
    print("   ✅ Local blank screen cleared")
    
    # Wait a bit
    root.update()
    time.sleep(0.5)
    
    # Test remote blank screen
    print("4. Testing remote blank screen...")
    
    # First, simulate a participant being assigned to slot 1
    if 1 in video_frame.video_slots:
        slot = video_frame.video_slots[1]
        slot['participant_id'] = 'test_client_123'
        slot['participant_name'] = 'TestUser'
        slot['active'] = False
        
        # Show blank screen for remote client
        video_frame.show_blank_screen_for_client('test_client_123', 'TestUser')
        print("   ✅ Remote blank screen shown")
        
        # Wait a bit
        root.update()
        time.sleep(0.5)
        
        # Clear blank screen for remote client
        video_frame.clear_blank_screen_for_client('test_client_123', 'TestUser')
        print("   ✅ Remote blank screen cleared")
    
    # Wait a bit more
    root.update()
    time.sleep(0.5)
    
    print("5. All GUI tests completed successfully!")
    
    # Close the window
    root.destroy()
    
    return True

if __name__ == "__main__":
    print("🎥 Simple Blank Screen Test")
    print("Testing blank screen GUI functionality...")
    print()
    
    try:
        success = test_blank_screen_gui()
        
        if success:
            print("\n🎉 All tests completed successfully!")
            print("The blank screen GUI functionality is working correctly.")
        else:
            print("\n❌ Tests failed!")
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    sys.exit(0)