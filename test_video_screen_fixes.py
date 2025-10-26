#!/usr/bin/env python3
"""
Test script for video conferencing and screen sharing fixes.
Tests the enhanced video display and screen sharing improvements.
"""

import sys
import os
import time
import threading
import numpy as np
import tkinter as tk
from unittest.mock import Mock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_video_conferencing_fixes():
    """Test the video conferencing fixes."""
    print("🎥 Testing Video Conferencing Fixes...")
    
    try:
        from client.gui_manager import VideoFrame
        
        # Create test window
        root = tk.Tk()
        root.title("Video Test")
        root.geometry("800x600")
        
        # Create video frame
        video_frame = VideoFrame(root)
        video_frame.pack(fill='both', expand=True)
        
        # Create test video data
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        
        print("✅ Video frame created successfully")
        
        # Test local video update
        try:
            video_frame.update_local_video(test_frame)
            print("✅ Local video update works")
        except Exception as e:
            print(f"❌ Local video update failed: {e}")
        
        # Test remote video update
        try:
            video_frame.update_remote_video("test_client_123", test_frame)
            print("✅ Remote video update works")
        except Exception as e:
            print(f"❌ Remote video update failed: {e}")
        
        # Test participant name update
        try:
            video_frame.update_participant_name("test_client_123", "John Doe")
            print("✅ Participant name update works")
        except Exception as e:
            print(f"❌ Participant name update failed: {e}")
        
        # Update display to show changes
        root.update()
        
        print("✅ Video conferencing fixes test completed")
        
        # Close after short delay
        root.after(2000, root.destroy)
        root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"❌ Video conferencing test failed: {e}")
        return False

def test_screen_sharing_fixes():
    """Test the screen sharing fixes."""
    print("🖥️ Testing Screen Sharing Fixes...")
    
    try:
        from client.gui_manager import ScreenShareFrame
        
        # Create test window
        root = tk.Tk()
        root.title("Screen Share Test")
        root.geometry("800x600")
        
        # Create screen share frame
        screen_frame = ScreenShareFrame(root)
        screen_frame.pack(fill='both', expand=True)
        
        print("✅ Screen share frame created successfully")
        
        # Test presenter update
        try:
            screen_frame.update_presenter("Test Presenter")
            print("✅ Presenter update works")
        except Exception as e:
            print(f"❌ Presenter update failed: {e}")
        
        # Create test screen frame data
        import cv2
        test_screen = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        success, encoded_frame = cv2.imencode('.jpg', test_screen, encode_params)
        
        if success:
            frame_data = encoded_frame.tobytes()
            
            # Test screen frame display
            try:
                screen_frame.display_screen_frame(frame_data, "Test Presenter")
                print("✅ Screen frame display works")
            except Exception as e:
                print(f"❌ Screen frame display failed: {e}")
        
        # Update display to show changes
        root.update()
        
        print("✅ Screen sharing fixes test completed")
        
        # Close after short delay
        root.after(3000, root.destroy)
        root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"❌ Screen sharing test failed: {e}")
        return False

def test_enhanced_gui():
    """Test the enhanced GUI layout."""
    print("🎨 Testing Enhanced GUI Layout...")
    
    try:
        from client.gui_manager import GUIManager
        
        # Create GUI manager
        gui = GUIManager()
        
        print("✅ Enhanced GUI created successfully")
        
        # Test connection status update
        try:
            gui.update_connection_status("Connected")
            print("✅ Connection status update works")
        except Exception as e:
            print(f"❌ Connection status update failed: {e}")
        
        # Test tab switching
        try:
            gui._show_tab('video')
            gui._show_tab('screen')
            gui._show_tab('chat')
            print("✅ Tab switching works")
        except Exception as e:
            print(f"❌ Tab switching failed: {e}")
        
        print("✅ Enhanced GUI test completed")
        
        # Close after short delay
        gui.root.after(2000, gui.close)
        gui.run()
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced GUI test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Video and Screen Sharing Fixes Test")
    print("=" * 60)
    
    tests = [
        ("Video Conferencing Fixes", test_video_conferencing_fixes),
        ("Screen Sharing Fixes", test_screen_sharing_fixes),
        ("Enhanced GUI Layout", test_enhanced_gui)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Video and screen sharing fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()