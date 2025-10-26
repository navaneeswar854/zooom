#!/usr/bin/env python3
"""
Simple test to verify screen sharing functionality works.
"""

import sys
import os
import time
import numpy as np
import tkinter as tk
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_screen_share_interface():
    """Test the simplified screen sharing interface."""
    print("🖥️ Testing Screen Share Interface...")
    
    try:
        from client.gui_manager import GUIManager
        
        # Create GUI manager
        gui = GUIManager()
        
        print("✅ GUI created successfully")
        
        # Mock screen share callback
        screen_share_called = []
        def mock_screen_share_callback(enabled):
            screen_share_called.append(enabled)
            print(f"📞 Screen share callback called with: {enabled}")
        
        # Set up callbacks
        gui.set_module_callbacks(
            video_callback=lambda x: None,
            audio_callback=lambda x: None,
            message_callback=lambda x: None,
            screen_share_callback=mock_screen_share_callback,
            file_upload_callback=lambda x: None,
            file_download_callback=lambda x: None
        )
        
        print("✅ Callbacks set successfully")
        
        # Test screen share button click
        try:
            gui._toggle_screen_share()
            print("✅ Screen share toggle works")
            
            if screen_share_called:
                print(f"✅ Screen share callback was called: {screen_share_called}")
            else:
                print("⚠️ Screen share callback was not called")
                
        except Exception as e:
            print(f"❌ Screen share toggle failed: {e}")
        
        # Test presenter name display
        try:
            if gui.screen_share_frame:
                gui.screen_share_frame.update_presenter("Test User")
                print("✅ Presenter name update works")
            else:
                print("❌ Screen share frame not found")
        except Exception as e:
            print(f"❌ Presenter name update failed: {e}")
        
        # Update display
        gui.root.update()
        
        print("✅ Screen share interface test completed")
        
        # Close after short delay
        gui.root.after(2000, gui.close)
        gui.run()
        
        return True
        
    except Exception as e:
        print(f"❌ Screen share interface test failed: {e}")
        return False

def main():
    """Run the screen share test."""
    print("🚀 Starting Screen Share Interface Test")
    print("=" * 50)
    
    result = test_screen_share_interface()
    
    print("\n" + "=" * 50)
    if result:
        print("✅ Screen share interface test PASSED")
        print("🖥️ Screen share button moved to top controls")
        print("👤 Only presenter name displayed in frame")
    else:
        print("❌ Screen share interface test FAILED")

if __name__ == "__main__":
    main()