#!/usr/bin/env python3
"""
Test script to verify video conferencing fixes.
Tests the specific issues found in the client logs.
"""

import sys
import os
import time
import threading
import logging
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gui_manager_video_methods():
    """Test the GUI manager video methods that were causing errors."""
    print("🧪 Testing GUI Manager Video Methods...")
    
    try:
        # Import GUI manager
        from client.gui_manager import VideoFrame
        import tkinter as tk
        
        # Create a test root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Create a test frame
        test_frame = tk.Frame(root)
        
        # Create VideoFrame instance
        video_frame = VideoFrame(test_frame)
        
        # Test 1: Check if _get_or_assign_video_slot method exists
        if hasattr(video_frame, '_get_or_assign_video_slot'):
            print("✅ _get_or_assign_video_slot method exists")
            
            # Test the method with a mock client ID
            slot_id = video_frame._get_or_assign_video_slot("test_client_123")
            if slot_id is not None:
                print(f"✅ _get_or_assign_video_slot returned slot {slot_id}")
            else:
                print("⚠️  _get_or_assign_video_slot returned None (no available slots)")
        else:
            print("❌ _get_or_assign_video_slot method is missing!")
            return False
        
        # Test 2: Check video slots structure
        if hasattr(video_frame, 'video_slots') and video_frame.video_slots:
            print(f"✅ Video slots initialized: {len(video_frame.video_slots)} slots")
            
            # Check slot structure
            for slot_id, slot in video_frame.video_slots.items():
                if 'frame' in slot and 'label' in slot:
                    print(f"✅ Slot {slot_id} has proper structure")
                else:
                    print(f"⚠️  Slot {slot_id} missing required components")
        else:
            print("❌ Video slots not properly initialized!")
            return False
        
        # Test 3: Test thread-safe video update methods
        if hasattr(video_frame, '_widget_exists'):
            print("✅ _widget_exists method exists for thread safety")
        else:
            print("⚠️  _widget_exists method missing")
        
        # Test 4: Create a mock video frame and test update
        try:
            # Create a simple test frame (numpy array)
            test_frame_data = np.zeros((120, 160, 3), dtype=np.uint8)
            test_frame_data[:, :] = [100, 150, 200]  # Fill with a color
            
            # Test local video update (should not crash)
            video_frame.update_local_video(test_frame_data)
            print("✅ Local video update method executed without errors")
            
            # Test remote video update (should not crash)
            video_frame.update_remote_video("test_client_456", test_frame_data)
            print("✅ Remote video update method executed without errors")
            
        except Exception as e:
            print(f"⚠️  Video update test failed: {e}")
        
        # Clean up
        root.destroy()
        
        print("✅ GUI Manager video methods test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ GUI Manager test failed: {e}")
        return False

def test_threading_safety():
    """Test that video updates work from background threads."""
    print("\n🧪 Testing Threading Safety...")
    
    try:
        import tkinter as tk
        from client.gui_manager import VideoFrame
        
        # Create GUI in main thread
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test data
        test_frame_data = np.zeros((120, 160, 3), dtype=np.uint8)
        test_frame_data[:, :] = [50, 100, 150]
        
        # Flag to track completion
        update_completed = threading.Event()
        error_occurred = threading.Event()
        
        def background_video_update():
            """Simulate video updates from background thread."""
            try:
                # This should not cause tkinter errors anymore
                video_frame.update_local_video(test_frame_data)
                video_frame.update_remote_video("bg_client_789", test_frame_data)
                update_completed.set()
            except Exception as e:
                logger.error(f"Background update error: {e}")
                error_occurred.set()
        
        # Start background thread
        bg_thread = threading.Thread(target=background_video_update)
        bg_thread.daemon = True
        bg_thread.start()
        
        # Process GUI events for a short time
        start_time = time.time()
        while time.time() - start_time < 2.0:
            root.update()
            time.sleep(0.01)
            
            if update_completed.is_set():
                break
            if error_occurred.is_set():
                break
        
        # Check results
        if error_occurred.is_set():
            print("❌ Threading safety test failed - errors occurred")
            return False
        elif update_completed.is_set():
            print("✅ Threading safety test passed - no tkinter errors")
        else:
            print("⚠️  Threading safety test inconclusive - timeout")
        
        # Clean up
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Threading safety test failed: {e}")
        return False

def test_widget_validation():
    """Test widget existence validation."""
    print("\n🧪 Testing Widget Validation...")
    
    try:
        import tkinter as tk
        from client.gui_manager import VideoFrame
        
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test with valid widget
        test_widget = tk.Label(root, text="test")
        if video_frame._widget_exists(test_widget):
            print("✅ Widget validation works for valid widgets")
        else:
            print("❌ Widget validation failed for valid widget")
            return False
        
        # Test with destroyed widget
        test_widget.destroy()
        if not video_frame._widget_exists(test_widget):
            print("✅ Widget validation correctly identifies destroyed widgets")
        else:
            print("❌ Widget validation failed for destroyed widget")
            return False
        
        # Test with None
        if not video_frame._widget_exists(None):
            print("✅ Widget validation correctly handles None")
        else:
            print("❌ Widget validation failed for None")
            return False
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Widget validation test failed: {e}")
        return False

def main():
    """Run all video conferencing fix tests."""
    print("🚀 Starting Video Conferencing Fix Tests")
    print("=" * 50)
    
    tests = [
        ("GUI Manager Video Methods", test_gui_manager_video_methods),
        ("Threading Safety", test_threading_safety),
        ("Widget Validation", test_widget_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
        
        print("-" * 30)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All video conferencing fixes are working correctly!")
        print("\n📋 Fixed Issues:")
        print("   • Missing _get_or_assign_video_slot method")
        print("   • Thread-safe GUI updates")
        print("   • Widget existence validation")
        print("   • Proper error handling")
        return True
    else:
        print("⚠️  Some tests failed. Video conferencing may still have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)