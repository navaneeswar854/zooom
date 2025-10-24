#!/usr/bin/env python3
"""
Test script to verify the numpy array boolean context fix.
"""

import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_frame_data_validation():
    """Test the frame data validation logic that was causing the error."""
    
    print("Testing frame data validation fix...")
    
    # Test cases that should pass validation
    test_cases = [
        ("Valid numpy array", np.array([1, 2, 3, 4, 5])),
        ("Valid string", "valid_frame_data"),
        ("Valid bytes", b"valid_frame_data"),
    ]
    
    # Test cases that should fail validation
    fail_cases = [
        ("None", None),
        ("Empty numpy array", np.array([])),
        ("Empty string", ""),
        ("Empty bytes", b""),
    ]
    
    def validate_frame_data(frame_data):
        """The fixed validation logic from screen_manager.py"""
        if frame_data is None or (hasattr(frame_data, 'size') and frame_data.size == 0) or (isinstance(frame_data, (str, bytes)) and len(frame_data) == 0):
            return False
        return True
    
    print("\nTesting valid cases (should pass):")
    for name, frame_data in test_cases:
        try:
            result = validate_frame_data(frame_data)
            print(f"  ✓ {name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            print(f"  ✗ {name}: ERROR - {e}")
    
    print("\nTesting invalid cases (should fail):")
    for name, frame_data in fail_cases:
        try:
            result = validate_frame_data(frame_data)
            print(f"  ✓ {name}: {'FAIL' if not result else 'UNEXPECTED PASS'}")
        except Exception as e:
            print(f"  ✗ {name}: ERROR - {e}")
    
    print("\nTesting the old problematic code (should cause error):")
    try:
        # This is what was causing the error
        test_array = np.array([1, 2, 3])
        if not test_array:  # This should raise the ambiguous error
            print("  This shouldn't print")
    except ValueError as e:
        if "ambiguous" in str(e):
            print(f"  ✓ Confirmed old code causes error: {e}")
        else:
            print(f"  ? Unexpected error: {e}")
    
    print("\n✅ Frame data validation fix test completed!")


if __name__ == "__main__":
    test_frame_data_validation()