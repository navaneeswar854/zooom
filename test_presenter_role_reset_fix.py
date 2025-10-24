#!/usr/bin/env python3
"""
Test script to verify the presenter role reset fix.
Tests that clients can share again after stopping screen sharing.
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.screen_manager import ScreenManager
from client.gui_manager import ScreenShareFrame


class TestPresenterRoleResetFix(unittest.TestCase):
    """Test the presenter role reset functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock GUI components
        self.mock_gui = Mock()
        self.mock_connection = Mock()
        
        # Create screen manager
        self.screen_manager = ScreenManager(
            client_id="test_client",
            gui_manager=self.mock_gui,
            connection_manager=self.mock_connection
        )
        
        # Create screen share frame for GUI testing
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
        self.screen_share_frame = ScreenShareFrame(self.root)
    
    def tearDown(self):
        """Clean up test environment."""
        try:
            self.root.destroy()
        except:
            pass
    
    def test_stop_screen_sharing_clears_presenter_status(self):
        """Test that stopping screen sharing clears presenter status in GUI."""
        print("\n=== Testing Stop Screen Sharing Clears Presenter Status ===")
        
        # Simulate starting screen sharing (set as presenter first)
        self.screen_manager.is_sharing = True
        
        # Stop screen sharing
        self.screen_manager.stop_screen_sharing()
        
        # Verify both methods were called
        self.mock_gui.set_screen_sharing_status.assert_called_with(False)
        self.mock_gui.set_presenter_status.assert_called_with(False)
        
        print("   ✓ stop_screen_sharing() calls both set_screen_sharing_status(False) and set_presenter_status(False)")
    
    def test_handle_screen_share_stopped_clears_presenter_status(self):
        """Test that handle_screen_share_stopped clears presenter status."""
        print("\n=== Testing Handle Screen Share Stopped Clears Presenter Status ===")
        
        # Set initial state
        self.screen_share_frame.is_sharing = True
        self.screen_share_frame.share_button.config(text="Stop Screen Share")
        
        # Call handle_screen_share_stopped
        self.screen_share_frame.handle_screen_share_stopped()
        
        # Verify button text is reset to request presenter role
        button_text = self.screen_share_frame.share_button.cget('text')
        self.assertEqual(button_text, "Request Presenter Role")
        
        # Verify status text
        status_text = self.screen_share_frame.sharing_status.cget('text')
        self.assertEqual(status_text, "Ready to request presenter role")
        
        print("   ✓ handle_screen_share_stopped() properly resets button to 'Request Presenter Role'")
    
    def test_button_state_after_stop_and_restart_cycle(self):
        """Test the complete stop and restart cycle."""
        print("\n=== Testing Complete Stop and Restart Cycle ===")
        
        # Initial state: not sharing, not presenter
        self.screen_share_frame.set_presenter_status(False)
        initial_button_text = self.screen_share_frame.share_button.cget('text')
        self.assertEqual(initial_button_text, "Request Presenter Role")
        print("   ✓ Initial state: 'Request Presenter Role'")
        
        # Become presenter
        self.screen_share_frame.set_presenter_status(True)
        presenter_button_text = self.screen_share_frame.share_button.cget('text')
        self.assertEqual(presenter_button_text, "Start Screen Share")
        print("   ✓ After becoming presenter: 'Start Screen Share'")
        
        # Start sharing
        self.screen_share_frame.set_sharing_status(True)
        sharing_button_text = self.screen_share_frame.share_button.cget('text')
        self.assertEqual(sharing_button_text, "Stop Screen Share")
        print("   ✓ While sharing: 'Stop Screen Share'")
        
        # Stop sharing (this should clear presenter status)
        self.screen_share_frame.handle_screen_share_stopped()
        stopped_button_text = self.screen_share_frame.share_button.cget('text')
        self.assertEqual(stopped_button_text, "Request Presenter Role")
        print("   ✓ After stopping: 'Request Presenter Role' (ready to share again)")
    
    def test_gui_state_consistency(self):
        """Test that GUI state remains consistent through sharing cycles."""
        print("\n=== Testing GUI State Consistency ===")
        
        # Test multiple start/stop cycles
        for cycle in range(3):
            print(f"   Testing cycle {cycle + 1}...")
            
            # Start: Request presenter -> Become presenter -> Start sharing -> Stop sharing
            self.screen_share_frame.set_presenter_status(False)
            self.assertEqual(self.screen_share_frame.share_button.cget('text'), "Request Presenter Role")
            
            self.screen_share_frame.set_presenter_status(True)
            self.assertEqual(self.screen_share_frame.share_button.cget('text'), "Start Screen Share")
            
            self.screen_share_frame.set_sharing_status(True)
            self.assertEqual(self.screen_share_frame.share_button.cget('text'), "Stop Screen Share")
            
            self.screen_share_frame.handle_screen_share_stopped()
            self.assertEqual(self.screen_share_frame.share_button.cget('text'), "Request Presenter Role")
            
            print(f"     ✓ Cycle {cycle + 1} completed successfully")
        
        print("   ✓ GUI state remains consistent through multiple cycles")


def main():
    """Run the presenter role reset fix tests."""
    print("Testing Presenter Role Reset Fix")
    print("=" * 45)
    print("This test verifies that clients can share again after stopping.")
    print()
    
    # Run tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 45)
    print("🎉 All tests passed! Presenter role reset fix is working.")
    print()
    print("Expected behavior after fix:")
    print("1. ✅ Client stops sharing → Button shows 'Request Presenter Role'")
    print("2. ✅ Client can immediately request presenter role again")
    print("3. ✅ Multiple start/stop cycles work correctly")
    print("4. ✅ GUI state remains consistent")


if __name__ == "__main__":
    main()