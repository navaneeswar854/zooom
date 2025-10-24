#!/usr/bin/env python3
"""
Test script to verify the screen frame format fix.
Tests that numpy arrays are properly converted to JPEG bytes for GUI display.
"""

import sys
import os
import numpy as np
import cv2
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.screen_manager import ScreenManager


def test_screen_frame_format_conversion():
    """Test that screen frames are properly converted from numpy arrays to JPEG bytes."""
    
    print("Testing screen frame format conversion...")
    
    # Create mock GUI manager to capture what gets passed to it
    mock_gui = Mock()
    mock_connection = Mock()
    
    # Create screen manager
    screen_manager = ScreenManager(
        client_id="test_client",
        gui_manager=mock_gui,
        connection_manager=mock_connection
    )
    
    # Create a test numpy array (simulating what screen playback would pass)
    test_frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    
    print(f"Test frame shape: {test_frame.shape}, dtype: {test_frame.dtype}")
    
    # Call the frame received callback with numpy array
    screen_manager._on_screen_frame_received(test_frame, "test_presenter")
    
    # Check that GUI display_screen_frame was called
    if mock_gui.display_screen_frame.called:
        # Get the arguments passed to the GUI
        args, kwargs = mock_gui.display_screen_frame.call_args
        frame_data, presenter_id = args
        
        print(f"GUI received data type: {type(frame_data)}")
        print(f"GUI received presenter: {presenter_id}")
        
        # Verify it's bytes (JPEG data)
        if isinstance(frame_data, bytes):
            print("✓ Frame data is bytes (correct format for GUI)")
            
            # Try to decode it as JPEG to verify it's valid
            try:
                import io
                from PIL import Image
                image = Image.open(io.BytesIO(frame_data))
                print(f"✓ Successfully decoded as JPEG image: {image.size}")
                
            except Exception as e:
                print(f"✗ Failed to decode as JPEG: {e}")
                return False
                
        else:
            print(f"✗ Frame data is {type(frame_data)}, expected bytes")
            return False
            
    else:
        print("✗ GUI display_screen_frame was not called")
        return False
    
    print("✅ Screen frame format conversion test PASSED!")
    return True


def test_empty_frame_handling():
    """Test that empty frames are properly handled."""
    
    print("\nTesting empty frame handling...")
    
    mock_gui = Mock()
    mock_connection = Mock()
    
    screen_manager = ScreenManager(
        client_id="test_client",
        gui_manager=mock_gui,
        connection_manager=mock_connection
    )
    
    # Test with None
    screen_manager._on_screen_frame_received(None, "test_presenter")
    
    # Test with empty numpy array
    empty_frame = np.array([])
    screen_manager._on_screen_frame_received(empty_frame, "test_presenter")
    
    # GUI should not have been called for empty frames
    if not mock_gui.display_screen_frame.called:
        print("✓ Empty frames properly rejected")
        return True
    else:
        print("✗ Empty frames were not rejected")
        return False


def test_bytes_passthrough():
    """Test that if bytes are passed, they go through unchanged."""
    
    print("\nTesting bytes passthrough...")
    
    mock_gui = Mock()
    mock_connection = Mock()
    
    screen_manager = ScreenManager(
        client_id="test_client",
        gui_manager=mock_gui,
        connection_manager=mock_connection
    )
    
    # Create test JPEG bytes
    test_frame = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
    success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
    test_jpeg_bytes = encoded_frame.tobytes()
    
    # Pass bytes directly
    screen_manager._on_screen_frame_received(test_jpeg_bytes, "test_presenter")
    
    if mock_gui.display_screen_frame.called:
        args, kwargs = mock_gui.display_screen_frame.call_args
        frame_data, presenter_id = args
        
        if frame_data == test_jpeg_bytes:
            print("✓ Bytes passed through unchanged")
            return True
        else:
            print("✗ Bytes were modified")
            return False
    else:
        print("✗ GUI was not called")
        return False


def main():
    """Run all screen frame format tests."""
    print("Testing Screen Frame Format Fix")
    print("=" * 40)
    
    tests = [
        test_screen_frame_format_conversion,
        test_empty_frame_handling,
        test_bytes_passthrough
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\n{passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All screen frame format tests PASSED!")
        print("The GUI should now be able to display screen frames correctly.")
    else:
        print("❌ Some tests failed. The fix may need adjustment.")


if __name__ == "__main__":
    main()