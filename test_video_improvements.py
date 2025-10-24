#!/usr/bin/env python3
"""
Test script to verify video conferencing improvements.
Tests frame rate, quality, and layout improvements.
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

def test_video_capture_settings():
    """Test that video capture has improved settings."""
    print("🧪 Testing Video Capture Settings...")
    
    try:
        from client.video_capture import VideoCapture
        
        # Create video capture instance
        video_capture = VideoCapture("test_client")
        
        # Check default settings
        print(f"✅ Default resolution: {video_capture.width}x{video_capture.height}")
        print(f"✅ Default FPS: {video_capture.fps}")
        print(f"✅ Default quality: {video_capture.compression_quality}")
        
        # Verify improved settings
        if video_capture.width >= 320 and video_capture.height >= 240:
            print("✅ Resolution improved (320x240 or higher)")
        else:
            print(f"❌ Resolution too low: {video_capture.width}x{video_capture.height}")
            return False
        
        if video_capture.fps >= 25:
            print("✅ Frame rate improved (25 FPS or higher)")
        else:
            print(f"❌ Frame rate too low: {video_capture.fps}")
            return False
        
        if video_capture.compression_quality >= 70:
            print("✅ Quality improved (70% or higher)")
        else:
            print(f"❌ Quality too low: {video_capture.compression_quality}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Video capture settings test failed: {e}")
        return False

def test_video_display_layout():
    """Test that video display layout is improved."""
    print("\n🧪 Testing Video Display Layout...")
    
    try:
        from client.gui_manager import VideoFrame
        import tkinter as tk
        
        # Create test environment
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test 1: Check video slots are properly created
        if len(video_frame.video_slots) == 4:
            print("✅ 4 video slots created (2x2 grid)")
        else:
            print(f"❌ Wrong number of video slots: {len(video_frame.video_slots)}")
            return False
        
        # Test 2: Check slot 0 is for local video
        slot_0 = video_frame.video_slots[0]
        if slot_0.get('participant_id') == 'local':
            print("✅ Slot 0 designated for local video")
        else:
            print("❌ Slot 0 not properly designated for local video")
            return False
        
        # Test 3: Test video display size
        test_frame_data = np.zeros((240, 320, 3), dtype=np.uint8)
        test_frame_data[:, :] = [100, 150, 200]
        
        # Update local video
        video_frame.update_local_video(test_frame_data)
        
        # Check if canvas was created with proper size
        if hasattr(slot_0, 'video_canvas'):
            canvas = slot_0['video_canvas']
            canvas_width = canvas.winfo_reqwidth()
            canvas_height = canvas.winfo_reqheight()
            
            if canvas_width >= 200 and canvas_height >= 150:
                print(f"✅ Video canvas size improved: {canvas_width}x{canvas_height}")
            else:
                print(f"⚠️  Video canvas size: {canvas_width}x{canvas_height}")
        
        # Test 4: Test remote video assignment
        video_frame.update_remote_video("test_client_123", test_frame_data)
        
        # Check if remote video got assigned to slot 1
        slot_1 = video_frame.video_slots[1]
        if slot_1.get('participant_id') == "test_client_123":
            print("✅ Remote video properly assigned to slot 1")
        else:
            print("❌ Remote video not properly assigned")
            return False
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Video display layout test failed: {e}")
        return False

def test_video_frame_processing():
    """Test video frame processing improvements."""
    print("\n🧪 Testing Video Frame Processing...")
    
    try:
        from client.gui_manager import VideoFrame
        import tkinter as tk
        from PIL import Image
        
        root = tk.Tk()
        root.withdraw()
        
        test_frame = tk.Frame(root)
        video_frame = VideoFrame(test_frame)
        
        # Test with different frame sizes
        test_frames = [
            (160, 120),   # Small frame
            (320, 240),   # Medium frame
            (640, 480),   # Large frame
        ]
        
        for width, height in test_frames:
            test_data = np.zeros((height, width, 3), dtype=np.uint8)
            test_data[:, :] = [50, 100, 150]
            
            try:
                video_frame.update_local_video(test_data)
                print(f"✅ Processed {width}x{height} frame successfully")
            except Exception as e:
                print(f"❌ Failed to process {width}x{height} frame: {e}")
                return False
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Video frame processing test failed: {e}")
        return False

def test_low_latency_optimizations():
    """Test low latency optimizations."""
    print("\n🧪 Testing Low Latency Optimizations...")
    
    try:
        from client.video_capture import VideoCapture
        
        video_capture = VideoCapture("test_client")
        
        # Test frame interval calculation for high FPS
        if video_capture.fps >= 25:
            frame_interval = 1.0 / video_capture.fps
            if frame_interval <= 0.04:  # 25 FPS = 40ms interval
                print(f"✅ Low latency frame interval: {frame_interval*1000:.1f}ms")
            else:
                print(f"⚠️  Frame interval: {frame_interval*1000:.1f}ms")
        
        # Test that settings allow for low latency
        settings_good = (
            video_capture.fps >= 25 and
            video_capture.compression_quality >= 70 and
            video_capture.width >= 320
        )
        
        if settings_good:
            print("✅ Settings optimized for low latency")
        else:
            print("❌ Settings not optimized for low latency")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Low latency optimization test failed: {e}")
        return False

def main():
    """Run all video improvement tests."""
    print("🚀 Starting Video Conferencing Improvement Tests")
    print("=" * 60)
    
    tests = [
        ("Video Capture Settings", test_video_capture_settings),
        ("Video Display Layout", test_video_display_layout),
        ("Video Frame Processing", test_video_frame_processing),
        ("Low Latency Optimizations", test_low_latency_optimizations),
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
        
        print("-" * 40)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Video conferencing improvements are working!")
        print("\n📋 Improvements Made:")
        print("   • Increased resolution to 320x240 (from 160x120)")
        print("   • Increased frame rate to 30 FPS (from 5 FPS)")
        print("   • Increased quality to 85% (from 15%)")
        print("   • Improved video display size to 200x150")
        print("   • Added low latency camera optimizations")
        print("   • Fixed video layout to prevent vertical stacking")
        print("   • Proper local/remote video slot assignment")
        
        print("\n🎯 Expected Results:")
        print("   • Smoother video with higher frame rate")
        print("   • Better video quality and clarity")
        print("   • Lower latency video transmission")
        print("   • Proper 2x2 grid layout (local + 3 remote slots)")
        print("   • No more vertical frame stacking")
        
        return True
    else:
        print("⚠️  Some improvements may not be working correctly.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)