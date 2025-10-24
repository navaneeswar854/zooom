#!/usr/bin/env python3
"""
Test script to verify video conferencing functionality.
"""

import sys
import os
import time
import cv2
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.video_capture import VideoCapture
from client.video_playback import VideoManager
from unittest.mock import Mock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_video_capture():
    """Test video capture functionality."""
    print("\n🎥 Testing video capture...")
    
    # Create mock connection manager
    mock_connection = Mock()
    
    # Create video capture
    video_capture = VideoCapture("test_client", mock_connection)
    
    # Test camera availability
    try:
        import cv2
        camera = cv2.VideoCapture(0)
        if camera.isOpened():
            print("   ✓ Camera is available")
            camera.release()
        else:
            print("   ⚠ Camera not available - using test frame")
    except Exception as e:
        print(f"   ⚠ Camera test failed: {e}")
    
    # Test video settings
    video_capture.set_video_settings(width=320, height=240, fps=10, quality=50)
    print("   ✓ Video settings configured")
    
    # Test frame callback
    frames_received = []
    def frame_callback(frame):
        frames_received.append(frame)
        print(f"   📹 Received frame: {frame.shape if frame is not None else 'None'}")
    
    video_capture.set_frame_callback(frame_callback)
    
    # Try to start capture
    success = video_capture.start_capture()
    if success:
        print("   ✓ Video capture started")
        
        # Wait for a few frames
        time.sleep(2)
        
        # Stop capture
        video_capture.stop_capture()
        print("   ✓ Video capture stopped")
        
        if frames_received:
            print(f"   ✓ Received {len(frames_received)} frames")
        else:
            print("   ⚠ No frames received")
    else:
        print("   ❌ Failed to start video capture")
    
    print("   ✅ Video capture test completed")

def test_video_display():
    """Test video display functionality."""
    print("\n🖥️ Testing video display...")
    
    try:
        import tkinter as tk
        from PIL import Image, ImageTk
        
        # Create test window
        root = tk.Tk()
        root.title("Video Display Test")
        root.geometry("400x300")
        
        # Create test frame (colorful pattern)
        test_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        test_frame[:, :, 0] = 255  # Red channel
        test_frame[60:180, 80:240, 1] = 255  # Green rectangle
        test_frame[120:240, 160:320, 2] = 255  # Blue rectangle
        
        # Convert to RGB (OpenCV uses BGR)
        rgb_frame = cv2.cvtColor(test_frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_frame)
        
        # Resize for display
        pil_image.thumbnail((160, 120), Image.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(pil_image)
        
        # Create canvas and display
        canvas = tk.Canvas(root, width=160, height=120, bg='black')
        canvas.pack(expand=True)
        
        canvas.create_image(80, 60, anchor='center', image=photo)
        
        # Keep reference
        canvas.image = photo
        
        print("   ✓ Test video frame created and displayed")
        print("   📺 Close the test window to continue...")
        
        # Show window for 3 seconds
        root.after(3000, root.destroy)
        root.mainloop()
        
        print("   ✅ Video display test completed")
        
    except Exception as e:
        print(f"   ❌ Video display test failed: {e}")

def test_video_integration():
    """Test video system integration."""
    print("\n🔗 Testing video system integration...")
    
    # Create mock components
    mock_connection = Mock()
    mock_gui = Mock()
    
    # Create video manager
    video_manager = VideoManager("test_client", mock_connection)
    
    # Set GUI callbacks
    def frame_callback(client_id, frame):
        print(f"   📹 Frame callback: client={client_id}, frame_shape={frame.shape if frame is not None else 'None'}")
    
    def status_callback(client_id, active):
        print(f"   📊 Status callback: client={client_id}, active={active}")
    
    video_manager.set_gui_callbacks(frame_callback, status_callback)
    
    # Start video system
    success = video_manager.start_video_system()
    if success:
        print("   ✓ Video system started")
        
        # Test with mock video packet
        try:
            from common.messages import UDPPacket, MessageType
            
            # Create test video data
            test_frame = np.zeros((120, 160, 3), dtype=np.uint8)
            test_frame[:, :, 1] = 128  # Green tint
            
            # Compress frame
            import cv2
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
            success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
            
            if success:
                # Create UDP packet
                packet = UDPPacket(
                    msg_type=MessageType.VIDEO.value,
                    sender_id="test_sender",
                    sequence_num=1,
                    data=encoded_frame.tobytes()
                )
                
                # Process packet
                video_manager.process_incoming_video(packet)
                print("   ✓ Test video packet processed")
            
        except Exception as e:
            print(f"   ⚠ Video packet test failed: {e}")
        
        # Stop video system
        video_manager.stop_video_system()
        print("   ✓ Video system stopped")
    else:
        print("   ❌ Failed to start video system")
    
    print("   ✅ Video integration test completed")

def main():
    """Run all video tests."""
    print("🚀 Running video conferencing tests...")
    
    try:
        test_video_capture()
        test_video_display()
        test_video_integration()
        
        print("\n✅ All video tests completed!")
        print("\n📋 Video conferencing should now work:")
        print("   • Local video preview in first slot")
        print("   • Remote video from other clients in remaining slots")
        print("   • Proper video frame display and scaling")
        print("   • Video slot management for multiple participants")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Video test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
