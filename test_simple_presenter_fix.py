#!/usr/bin/env python3
"""
Simple test to verify presenter role reset fix.
"""

import sys
import os
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.screen_manager import ScreenManager


def test_presenter_role_clearing():
    """Test that presenter role is cleared when screen sharing stops."""
    
    print("Testing presenter role clearing fix...")
    
    # Create mock components
    mock_gui = Mock()
    mock_connection = Mock()
    
    # Create screen manager
    screen_manager = ScreenManager(
        client_id="test_client",
        gui_manager=mock_gui,
        connection_manager=mock_connection
    )
    
    # Simulate starting screen sharing
    screen_manager.is_sharing = True
    
    # Stop screen sharing
    screen_manager.stop_screen_sharing()
    
    # Check that both GUI methods were called
    calls = mock_gui.method_calls
    call_names = [call[0] for call in calls]
    
    if 'set_screen_sharing_status' in call_names and 'set_presenter_status' in call_names:
        print("✅ Both set_screen_sharing_status(False) and set_presenter_status(False) were called")
        
        # Check the arguments
        for call in calls:
            if call[0] == 'set_screen_sharing_status':
                if call[1][0] == False:  # First argument should be False
                    print("✅ set_screen_sharing_status called with False")
            elif call[0] == 'set_presenter_status':
                if call[1][0] == False:  # First argument should be False
                    print("✅ set_presenter_status called with False")
        
        return True
    else:
        print(f"❌ Missing method calls. Found: {call_names}")
        return False


def main():
    """Run the simple presenter role test."""
    print("Simple Presenter Role Reset Test")
    print("=" * 35)
    
    if test_presenter_role_clearing():
        print("\n🎉 Test PASSED! The fix should work correctly.")
        print("\nExpected behavior:")
        print("- When client stops sharing, presenter status is cleared")
        print("- Button will show 'Request Presenter Role' instead of 'Start Screen Share'")
        print("- Client can request presenter role again to share")
    else:
        print("\n❌ Test FAILED! The fix needs adjustment.")


if __name__ == "__main__":
    main()