#!/usr/bin/env python3
"""
Test script to verify the screen sharing state fix.
Tests that active_screen_sharer is properly set and cleared.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.session_manager import SessionManager


class TestScreenSharingStateFix(unittest.TestCase):
    """Test the screen sharing state management fix."""
    
    def setUp(self):
        """Set up test environment."""
        self.session_manager = SessionManager()
        
        # Add a test client
        mock_socket = Mock()
        self.client_id = self.session_manager.add_client(mock_socket, "TestUser")
        
        # Set client as presenter
        self.session_manager.set_presenter(self.client_id)
    
    def test_start_screen_sharing_sets_active_sharer(self):
        """Test that starting screen sharing sets active_screen_sharer."""
        # Start screen sharing
        success, message = self.session_manager.start_screen_sharing(self.client_id)
        
        # Verify success
        self.assertTrue(success)
        self.assertEqual(message, "Screen sharing started successfully")
        
        # Verify state is set correctly
        self.assertTrue(self.session_manager.is_screen_sharing_active())
        self.assertEqual(self.session_manager.get_active_screen_sharer(), self.client_id)
        
        print("✓ start_screen_sharing correctly sets active_screen_sharer")
    
    def test_stop_screen_sharing_clears_active_sharer(self):
        """Test that stopping screen sharing clears active_screen_sharer."""
        # Start screen sharing first
        self.session_manager.start_screen_sharing(self.client_id)
        
        # Verify it's active
        self.assertTrue(self.session_manager.is_screen_sharing_active())
        self.assertEqual(self.session_manager.get_active_screen_sharer(), self.client_id)
        
        # Stop screen sharing
        success, message = self.session_manager.stop_screen_sharing(self.client_id)
        
        # Verify success
        self.assertTrue(success)
        self.assertEqual(message, "Screen sharing stopped successfully")
        
        # Verify state is cleared correctly
        self.assertFalse(self.session_manager.is_screen_sharing_active())
        self.assertIsNone(self.session_manager.get_active_screen_sharer())
        
        print("✓ stop_screen_sharing correctly clears active_screen_sharer")
    
    def test_stop_screen_sharing_clears_presenter_role(self):
        """Test that stopping screen sharing clears presenter role."""
        # Start screen sharing first
        self.session_manager.start_screen_sharing(self.client_id)
        
        # Verify presenter is set
        self.assertEqual(self.session_manager.get_active_presenter(), self.client_id)
        
        # Stop screen sharing
        success, message = self.session_manager.stop_screen_sharing(self.client_id)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify presenter role is cleared
        self.assertIsNone(self.session_manager.get_active_presenter())
        
        # Verify client's presenter flag is cleared
        client = self.session_manager.get_client(self.client_id)
        self.assertFalse(client.is_presenter)
        
        print("✓ stop_screen_sharing correctly clears presenter role")
    
    def test_screen_frame_validation_logic(self):
        """Test that screen frames are only accepted from active sharer."""
        # Start screen sharing
        self.session_manager.start_screen_sharing(self.client_id)
        
        # Verify frames from active sharer would be accepted
        active_sharer = self.session_manager.get_active_screen_sharer()
        self.assertEqual(active_sharer, self.client_id)
        
        # Add another client
        mock_socket2 = Mock()
        client_id_2 = self.session_manager.add_client(mock_socket2, "TestUser2")
        
        # Verify frames from non-active sharer would be rejected
        self.assertNotEqual(self.session_manager.get_active_screen_sharer(), client_id_2)
        
        print("✓ Screen frame validation logic works correctly")
    
    def test_multiple_presenter_requests_after_stop(self):
        """Test that presenter role can be requested after previous presenter stops."""
        # Start and stop screen sharing with first client
        self.session_manager.start_screen_sharing(self.client_id)
        self.session_manager.stop_screen_sharing(self.client_id)
        
        # Add second client
        mock_socket2 = Mock()
        client_id_2 = self.session_manager.add_client(mock_socket2, "TestUser2")
        
        # Second client should be able to request presenter role
        success, message = self.session_manager.request_presenter_role(client_id_2)
        
        self.assertTrue(success)
        self.assertEqual(message, "Presenter role granted")
        self.assertEqual(self.session_manager.get_active_presenter(), client_id_2)
        
        print("✓ Presenter role can be requested after previous presenter stops")


def main():
    """Run the screen sharing state fix tests."""
    print("Testing Screen Sharing State Fix")
    print("=" * 40)
    
    # Run tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 40)
    print("Screen sharing state fix tests completed!")


if __name__ == "__main__":
    main()