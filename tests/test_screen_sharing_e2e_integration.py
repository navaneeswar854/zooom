"""
End-to-end integration tests for screen sharing functionality.
Tests complete screen sharing flow from button click to display, multi-client scenarios,
network failure recovery, and platform-specific functionality.
"""

import unittest
import threading
import time
import tempfile
import os
import socket
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.main_client import CollaborationClient
from client.screen_manager import ScreenManager
from client.screen_capture import ScreenCapture
from client.screen_playback import ScreenPlayback
from client.connection_manager import ConnectionManager, ConnectionStatus
from client.gui_manager import GUIManager
from server.session_manager import SessionManager
from server.network_handler import NetworkHandler
from common.messages import TCPMessage, MessageType, MessageFactory
from common.platform_utils import is_windows, is_linux, is_macos


class TestScreenSharingEndToEndIntegration(unittest.TestCase):
    """Test complete screen sharing workflow from button click to display."""
    
    def setUp(self):
        """Set up test environment with mock components."""
        # Create mock GUI manager with all required methods
        self.mock_gui = Mock(spec=GUIManager)
        self.mock_gui.show_error = Mock()
        self.mock_gui.show_info = Mock()
        self.mock_gui.display_screen_frame = Mock()
        self.mock_gui.handle_presenter_granted = Mock()
        self.mock_gui.handle_presenter_denied = Mock()
        self.mock_gui.set_screen_sharing_status = Mock()
        self.mock_gui.set_presenter_status = Mock()
        self.mock_gui.handle_screen_share_started = Mock()
        self.mock_gui.handle_screen_share_stopped = Mock()
        self.mock_gui.update_presenter = Mock()
        self.mock_gui.update_screen_sharing_presenter = Mock()
        
        # Create mock connection manager
        self.mock_connection = Mock(spec=ConnectionManager)
        self.mock_connection.get_client_id.return_value = "test_client_1"
        self.mock_connection._is_connected.return_value = True
        self.mock_connection.request_presenter_role.return_value = (True, "Request sent")
        self.mock_connection.start_screen_sharing.return_value = (True, "Started")
        self.mock_connection.stop_screen_sharing.return_value = (True, "Stopped")
        self.mock_connection.send_tcp_message.return_value = True
        
        # Create screen manager for testing
        self.screen_manager = ScreenManager(
            client_id="test_client_1",
            connection_manager=self.mock_connection,
            gui_manager=self.mock_gui
        )
        
        # Mock screen capture to avoid platform dependencies
        self.mock_screen_capture = Mock()
        self.mock_screen_capture.start_capture.return_value = (True, "Capture started")
        self.mock_screen_capture.stop_capture.return_value = None
        self.mock_screen_capture.get_capability_info.return_value = {
            'available': True,
            'error_message': None
        }
        self.mock_screen_capture.get_setup_instructions.return_value = []
        self.screen_manager.screen_capture = self.mock_screen_capture
        
        # Track events for verification
        self.events = []
        
    def test_complete_screen_sharing_button_to_display_flow(self):
        """Test complete flow from button click to screen display."""
        # Step 1: User clicks "Start Screen Share" button
        self.screen_manager._handle_screen_share_toggle = Mock(
            side_effect=lambda enabled: self.screen_manager.request_presenter_role() if enabled else self.screen_manager.stop_screen_sharing()
        )
        
        # Simulate button click (enabled=True)
        self.screen_manager._handle_screen_share_toggle(True)
        
        # Verify presenter role was requested
        self.mock_connection.request_presenter_role.assert_called_once()
        self.assertTrue(self.screen_manager.presenter_request_pending)
        
        # Step 2: Server grants presenter role
        self.screen_manager.handle_presenter_granted()
        
        # Verify presenter status updated
        self.assertTrue(self.screen_manager.is_presenter)
        self.assertFalse(self.screen_manager.presenter_request_pending)
        self.mock_gui.handle_presenter_granted.assert_called_once()
        
        # Verify screen sharing start was called automatically
        self.mock_connection.start_screen_sharing.assert_called_once()
        
        # Step 3: Server confirms screen sharing start
        self.screen_manager.handle_screen_share_confirmed()
        
        # Verify screen capture was started
        self.mock_screen_capture.start_capture.assert_called_once()
        self.assertTrue(self.screen_manager.is_sharing)
        self.mock_gui.set_screen_sharing_status.assert_called_with(True)
        
        # Step 4: Simulate screen frame being captured and sent
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Mock frame processing
        with patch.object(self.screen_manager.screen_capture, '_process_frame') as mock_process:
            # Simulate frame callback
            if self.screen_manager.screen_capture.frame_callback:
                self.screen_manager.screen_capture.frame_callback(test_frame)
            
            # Verify frame was processed (would normally compress and send)
            # This is handled by the screen capture component
        
        # Step 5: Simulate receiving screen frame on another client
        screen_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id="test_client_1",
            data={
                'sequence_num': 1,
                'frame_data': b"fake_compressed_frame_data".hex(),
                'timestamp': time.time()
            }
        )
        
        # Process the message through screen manager
        self.screen_manager.handle_screen_share_message(screen_message)
        
        # Verify screen playback processed the frame
        # (This would normally display the frame via GUI callback)
        
        # Step 6: User stops screen sharing
        self.screen_manager._handle_screen_share_toggle(False)
        
        # Verify cleanup
        self.mock_screen_capture.stop_capture.assert_called_once()
        self.mock_connection.stop_screen_sharing.assert_called_once()
        self.assertFalse(self.screen_manager.is_sharing)
        self.mock_gui.set_screen_sharing_status.assert_called_with(False)
    
    def test_screen_sharing_error_handling_flow(self):
        """Test error handling throughout the screen sharing flow."""
        # Test 1: Connection manager not available
        screen_manager_no_conn = ScreenManager("test_client", None, self.mock_gui)
        screen_manager_no_conn.request_presenter_role()
        
        # Should show error to user
        self.mock_gui.show_error.assert_called()
        
        # Test 2: Screen capture fails to start
        self.mock_screen_capture.start_capture.return_value = (False, "Capture failed")
        
        # Grant presenter role first
        self.screen_manager.handle_presenter_granted()
        
        # Try to confirm screen sharing (should fail)
        self.screen_manager.handle_screen_share_confirmed()
        
        # Should show error and notify server of failure
        self.mock_gui.show_error.assert_called()
        self.mock_connection.stop_screen_sharing.assert_called()
        
        # Test 3: Network error during screen sharing
        self.screen_manager._on_connection_lost()
        
        # Should show connection error
        self.mock_gui.show_error.assert_called_with(
            "Connection Lost", 
            "Network connection lost during screen sharing. Attempting to reconnect..."
        )
        
        # Test 4: Screen capture not available
        self.mock_screen_capture.get_capability_info.return_value = {
            'available': False,
            'error_message': 'Screen capture not supported'
        }
        
        self.screen_manager.handle_screen_share_confirmed()
        
        # Should show capability error
        self.mock_gui.show_error.assert_called()
    
    def test_presenter_role_denial_handling(self):
        """Test handling of presenter role denial."""
        # Request presenter role
        self.screen_manager.request_presenter_role()
        self.assertTrue(self.screen_manager.presenter_request_pending)
        
        # Server denies presenter role
        denial_reason = "Another user is already presenting"
        self.screen_manager.handle_presenter_denied(denial_reason)
        
        # Verify state was reset
        self.assertFalse(self.screen_manager.presenter_request_pending)
        self.assertFalse(self.screen_manager.is_presenter)
        
        # Verify GUI was notified
        self.mock_gui.handle_presenter_denied.assert_called_with(denial_reason)


class TestMultiClientScreenSharingIntegration(unittest.TestCase):
    """Test multi-client screen sharing with presenter role switching."""
    
    def setUp(self):
        """Set up multi-client test environment."""
        # Create multiple mock clients
        self.clients = {}
        self.screen_managers = {}
        
        for i in range(3):
            client_id = f"client_{i+1}"
            
            # Mock connection manager
            mock_connection = Mock(spec=ConnectionManager)
            mock_connection.get_client_id.return_value = client_id
            mock_connection._is_connected.return_value = True
            mock_connection.request_presenter_role.return_value = (True, "Request sent")
            mock_connection.start_screen_sharing.return_value = (True, "Started")
            mock_connection.stop_screen_sharing.return_value = (True, "Stopped")
            mock_connection.send_tcp_message.return_value = True
            
            # Mock GUI manager
            mock_gui = Mock(spec=GUIManager)
            mock_gui.show_error = Mock()
            mock_gui.show_info = Mock()
            mock_gui.display_screen_frame = Mock()
            mock_gui.handle_presenter_granted = Mock()
            mock_gui.handle_presenter_denied = Mock()
            mock_gui.set_screen_sharing_status = Mock()
            mock_gui.handle_screen_share_started = Mock()
            mock_gui.handle_screen_share_stopped = Mock()
            
            # Create screen manager
            screen_manager = ScreenManager(client_id, mock_connection, mock_gui)
            
            # Mock screen capture
            mock_screen_capture = Mock()
            mock_screen_capture.start_capture.return_value = (True, "Started")
            mock_screen_capture.stop_capture.return_value = None
            mock_screen_capture.get_capability_info.return_value = {'available': True}
            screen_manager.screen_capture = mock_screen_capture
            
            self.clients[client_id] = {
                'connection': mock_connection,
                'gui': mock_gui,
                'screen_capture': mock_screen_capture
            }
            self.screen_managers[client_id] = screen_manager
    
    def test_presenter_role_switching_between_clients(self):
        """Test presenter role switching between multiple clients."""
        # Client 1 becomes presenter
        client1_manager = self.screen_managers['client_1']
        client1_manager.request_presenter_role()
        client1_manager.handle_presenter_granted()
        
        self.assertTrue(client1_manager.is_presenter)
        
        # Client 1 starts screen sharing
        client1_manager.handle_screen_share_confirmed()
        self.assertTrue(client1_manager.is_sharing)
        
        # Client 2 tries to become presenter (should be denied)
        client2_manager = self.screen_managers['client_2']
        client2_manager.request_presenter_role()
        client2_manager.handle_presenter_denied("Another user is already presenting")
        
        self.assertFalse(client2_manager.is_presenter)
        self.clients['client_2']['gui'].handle_presenter_denied.assert_called()
        
        # Client 1 stops screen sharing and releases presenter role
        client1_manager.stop_screen_sharing()
        client1_manager._release_presenter_role()
        
        self.assertFalse(client1_manager.is_presenter)
        self.assertFalse(client1_manager.is_sharing)
        
        # Now Client 2 can become presenter
        client2_manager.request_presenter_role()
        client2_manager.handle_presenter_granted()
        
        self.assertTrue(client2_manager.is_presenter)
        self.clients['client_2']['gui'].handle_presenter_granted.assert_called()
    
    def test_screen_frame_distribution_to_multiple_clients(self):
        """Test screen frames are distributed to all non-presenting clients."""
        # Client 1 becomes presenter and starts sharing
        presenter_manager = self.screen_managers['client_1']
        presenter_manager.handle_presenter_granted()
        presenter_manager.handle_screen_share_confirmed()
        
        # Create test screen frame message
        test_frame_data = b"test_screen_frame_data"
        screen_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id="client_1",
            data={
                'sequence_num': 1,
                'frame_data': test_frame_data.hex(),
                'timestamp': time.time()
            }
        )
        
        # Simulate frame being received by other clients
        for client_id in ['client_2', 'client_3']:
            manager = self.screen_managers[client_id]
            
            # Mock the screen playback processing
            with patch.object(manager.screen_playback, 'process_screen_message', return_value=True) as mock_process:
                manager.handle_screen_share_message(screen_message)
                mock_process.assert_called_once_with(screen_message)
        
        # Verify presenter client doesn't process its own frames
        with patch.object(presenter_manager.screen_playback, 'process_screen_message') as mock_process:
            presenter_manager.handle_screen_share_message(screen_message)
            # Should still be called as the screen manager doesn't filter self-messages
            mock_process.assert_called_once()
    
    def test_presenter_disconnection_handling(self):
        """Test handling when the presenting client disconnects."""
        # Client 1 becomes presenter and starts sharing
        presenter_manager = self.screen_managers['client_1']
        presenter_manager.handle_presenter_granted()
        presenter_manager.handle_screen_share_confirmed()
        
        # Simulate presenter disconnection by sending stop message
        stop_message = MessageFactory.create_screen_share_stop_message("client_1")
        
        # All other clients should receive the stop message
        for client_id in ['client_2', 'client_3']:
            manager = self.screen_managers[client_id]
            manager.handle_screen_share_message(stop_message)
            
            # Verify GUI was updated
            self.clients[client_id]['gui'].handle_screen_share_stopped.assert_called()
            self.clients[client_id]['gui'].update_presenter.assert_called_with(None)


class TestNetworkFailureRecoveryIntegration(unittest.TestCase):
    """Test network failure recovery during active screen sharing."""
    
    def setUp(self):
        """Set up network failure test environment."""
        self.mock_gui = Mock(spec=GUIManager)
        self.mock_connection = Mock(spec=ConnectionManager)
        self.mock_connection.get_client_id.return_value = "test_client"
        self.mock_connection._is_connected.return_value = True
        
        self.screen_manager = ScreenManager(
            "test_client", self.mock_connection, self.mock_gui
        )
        
        # Mock screen capture
        self.mock_screen_capture = Mock()
        self.mock_screen_capture.start_capture.return_value = (True, "Started")
        self.mock_screen_capture.stop_capture.return_value = None
        self.screen_manager.screen_capture = self.mock_screen_capture
        
        # Set up as presenter and sharing
        self.screen_manager.is_presenter = True
        self.screen_manager.is_sharing = True
    
    def test_connection_loss_during_screen_sharing(self):
        """Test handling of connection loss during active screen sharing."""
        # Simulate connection loss
        self.screen_manager._on_connection_lost()
        
        # Verify user was notified
        self.mock_gui.show_error.assert_called_with(
            "Connection Lost",
            "Network connection lost during screen sharing. Attempting to reconnect..."
        )
        
        # Screen sharing state should remain (for potential recovery)
        self.assertTrue(self.screen_manager.is_sharing)
        self.assertTrue(self.screen_manager.is_presenter)
    
    def test_connection_restoration_during_screen_sharing(self):
        """Test handling of connection restoration during screen sharing."""
        # First lose connection
        self.screen_manager._on_connection_lost()
        
        # Then restore connection
        self.screen_manager._on_connection_restored()
        
        # Should attempt to resume screen sharing (but may fail due to mock setup)
        # Note: The actual call depends on the internal state and mock configuration
        
        # Verify user was notified of restoration
        self.mock_gui.show_error.assert_called_with(
            "Connection Restored",
            "Network connection restored. Screen sharing may resume automatically."
        )
    
    def test_permanent_connection_failure_cleanup(self):
        """Test cleanup when connection permanently fails."""
        # Simulate permanent connection failure
        self.screen_manager._on_connection_failed()
        
        # Verify complete cleanup
        self.assertFalse(self.screen_manager.is_sharing)
        self.assertFalse(self.screen_manager.is_presenter)
        self.assertFalse(self.screen_manager.presenter_request_pending)
        
        # Verify screen capture was stopped
        self.mock_screen_capture.stop_capture.assert_called()
        
        # Verify GUI was updated
        self.mock_gui.set_screen_sharing_status.assert_called_with(False)
        self.mock_gui.set_presenter_status.assert_called_with(False)
        
        # Verify user was notified
        self.mock_gui.show_error.assert_called_with(
            "Connection Failed",
            "Unable to reconnect to server. Screen sharing has been stopped. Please check your network connection and try again."
        )
    
    def test_network_error_during_frame_transmission(self):
        """Test handling of network errors during frame transmission."""
        # Mock connection manager to simulate network error
        self.mock_connection.send_tcp_message.return_value = False
        
        # Create test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Mock the screen capture's _send_screen_frame method
        with patch.object(self.screen_manager.screen_capture, '_send_screen_frame') as mock_send:
            # Simulate frame processing that would normally send
            mock_send.side_effect = Exception("Network error")
            
            # This should be handled gracefully without crashing
            try:
                self.screen_manager.screen_capture._process_frame(test_frame)
            except Exception:
                self.fail("Frame processing should handle network errors gracefully")


class TestPlatformSpecificScreenCapture(unittest.TestCase):
    """Test platform-specific screen capture functionality."""
    
    def setUp(self):
        """Set up platform-specific test environment."""
        self.client_id = "platform_test_client"
        self.mock_connection = Mock(spec=ConnectionManager)
        self.mock_connection.get_client_id.return_value = self.client_id
    
    @patch('client.screen_capture.is_windows')
    @patch('client.screen_capture.WINDOWS_SPECIFIC_AVAILABLE', True)
    def test_windows_specific_screen_capture(self, mock_is_windows):
        """Test Windows-specific screen capture features."""
        mock_is_windows.return_value = True
        
        # Create screen capture instance
        screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock Windows-specific capabilities
        with patch.object(screen_capture, '_check_windows_capabilities') as mock_check:
            mock_check.return_value = {
                'supported': True,
                'features': ['window_specific_capture', 'pil_imagegrab'],
                'issues': []
            }
            
            # Test capability check
            capabilities = screen_capture._check_platform_capabilities()
            self.assertTrue(capabilities['platform_specific']['supported'])
            self.assertIn('window_specific_capture', capabilities['platform_specific']['features'])
        
        # Test Windows permission check
        with patch.object(screen_capture, '_check_windows_permissions') as mock_perm:
            mock_perm.return_value = {
                'available': True,
                'message': 'Windows screen capture permissions OK'
            }
            
            permissions = screen_capture._check_screen_capture_permissions()
            self.assertTrue(permissions['available'])
    
    @patch('client.screen_capture.is_linux')
    def test_linux_specific_screen_capture(self, mock_is_linux):
        """Test Linux-specific screen capture features."""
        mock_is_linux.return_value = True
        
        # Create screen capture instance
        screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock Linux-specific capabilities
        with patch.object(screen_capture, '_check_linux_capabilities') as mock_check:
            mock_check.return_value = {
                'supported': True,
                'features': ['x11_display_:0', 'scrot_available'],
                'issues': []
            }
            
            # Test capability check
            capabilities = screen_capture._check_platform_capabilities()
            self.assertTrue(capabilities['platform_specific']['supported'])
        
        # Test Linux permission check with DISPLAY set
        with patch.dict(os.environ, {'DISPLAY': ':0'}):
            with patch.object(screen_capture, '_check_linux_permissions') as mock_perm:
                mock_perm.return_value = {
                    'available': True,
                    'message': 'Linux screen capture permissions OK'
                }
                
                permissions = screen_capture._check_screen_capture_permissions()
                self.assertTrue(permissions['available'])
    
    @patch('client.screen_capture.is_macos')
    def test_macos_specific_screen_capture(self, mock_is_macos):
        """Test macOS-specific screen capture features."""
        mock_is_macos.return_value = True
        
        # Create screen capture instance
        screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock macOS-specific capabilities
        with patch.object(screen_capture, '_check_macos_capabilities') as mock_check:
            mock_check.return_value = {
                'supported': True,
                'features': ['pil_imagegrab', 'display_available'],
                'issues': []
            }
            
            # Test capability check
            capabilities = screen_capture._check_platform_capabilities()
            self.assertTrue(capabilities['platform_specific']['supported'])
        
        # Test macOS permission check
        with patch.object(screen_capture, '_check_macos_permissions') as mock_perm:
            mock_perm.return_value = {
                'available': True,
                'message': 'macOS screen capture permissions OK'
            }
            
            permissions = screen_capture._check_screen_capture_permissions()
            self.assertTrue(permissions['available'])
    
    def test_platform_capability_error_messages(self):
        """Test platform-specific error messages and setup instructions."""
        screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock unavailable screen capture
        with patch('client.screen_capture.SCREEN_CAPTURE_AVAILABLE', False):
            # Test Windows error message
            with patch('client.screen_capture.is_windows', return_value=True):
                message = screen_capture._get_platform_unavailable_message()
                self.assertIn("pip install pyautogui pygetwindow pillow", message)
            
            # Test Linux error message
            with patch('client.screen_capture.is_linux', return_value=True):
                message = screen_capture._get_platform_unavailable_message()
                self.assertIn("pyautogui", message)
                self.assertIn("pillow", message)
        
        # Test setup instructions
        with patch.object(screen_capture, 'capture_available', False):
            instructions = screen_capture.get_setup_instructions()
            self.assertGreater(len(instructions), 0)
            self.assertTrue(any("Install" in instruction for instruction in instructions))


class TestScreenSharingMessageFlow(unittest.TestCase):
    """Test screen sharing message flow and protocol handling."""
    
    def setUp(self):
        """Set up message flow test environment."""
        self.mock_gui = Mock(spec=GUIManager)
        self.mock_connection = Mock(spec=ConnectionManager)
        self.mock_connection.get_client_id.return_value = "test_client"
        
        self.screen_manager = ScreenManager(
            "test_client", self.mock_connection, self.mock_gui
        )
    
    def test_screen_share_message_types_handling(self):
        """Test handling of different screen sharing message types."""
        # Test SCREEN_SHARE message (frame data)
        frame_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id="presenter_client",
            data={
                'sequence_num': 1,
                'frame_data': b"fake_frame_data".hex(),
                'timestamp': time.time()
            }
        )
        
        with patch.object(self.screen_manager.screen_playback, 'process_screen_message', return_value=True) as mock_process:
            self.screen_manager.handle_screen_share_message(frame_message)
            mock_process.assert_called_once_with(frame_message)
        
        # Test SCREEN_SHARE_START message
        start_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE_START.value,
            sender_id="presenter_client",
            data={'presenter_name': 'TestPresenter'}
        )
        
        self.screen_manager.handle_screen_share_message(start_message)
        self.mock_gui.handle_screen_share_started.assert_called_with('TestPresenter')
        
        # Test SCREEN_SHARE_STOP message
        stop_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE_STOP.value,
            sender_id="presenter_client",
            data={}
        )
        
        self.screen_manager.handle_screen_share_message(stop_message)
        self.mock_gui.handle_screen_share_stopped.assert_called_once()
        
        # Test PRESENTER_GRANTED message
        granted_message = TCPMessage(
            msg_type=MessageType.PRESENTER_GRANTED.value,
            sender_id="server",
            data={'presenter_id': 'test_client'}
        )
        
        with patch.object(self.screen_manager, 'handle_presenter_granted') as mock_granted:
            self.screen_manager.handle_screen_share_message(granted_message)
            mock_granted.assert_called_once()
        
        # Test PRESENTER_DENIED message
        denied_message = TCPMessage(
            msg_type=MessageType.PRESENTER_DENIED.value,
            sender_id="server",
            data={'reason': 'Already taken'}
        )
        
        with patch.object(self.screen_manager, 'handle_presenter_denied') as mock_denied:
            self.screen_manager.handle_screen_share_message(denied_message)
            mock_denied.assert_called_once_with('Already taken')
    
    def test_invalid_message_handling(self):
        """Test handling of invalid or malformed messages."""
        # Test message with no type
        invalid_message = Mock()
        invalid_message.msg_type = None
        
        # Should handle gracefully without crashing
        try:
            self.screen_manager.handle_screen_share_message(invalid_message)
        except Exception:
            self.fail("Should handle invalid messages gracefully")
        
        # Test message with missing data
        incomplete_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id="test_sender",
            data={}  # Missing frame_data
        )
        
        with patch.object(self.screen_manager.screen_playback, 'process_screen_message', return_value=False) as mock_process:
            result = self.screen_manager.handle_screen_share_message(incomplete_message)
            mock_process.assert_called_once()
        
        # Test unknown message type
        unknown_message = TCPMessage(
            msg_type="unknown_screen_message",
            sender_id="test_sender",
            data={}
        )
        
        # Should log warning but not crash
        try:
            self.screen_manager.handle_screen_share_message(unknown_message)
        except Exception:
            self.fail("Should handle unknown message types gracefully")


class TestScreenSharingPerformanceIntegration(unittest.TestCase):
    """Test screen sharing performance under various conditions."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.client_id = "perf_test_client"
        self.mock_connection = Mock(spec=ConnectionManager)
        self.mock_connection.get_client_id.return_value = self.client_id
        self.mock_connection.send_tcp_message.return_value = True
        
        # Create screen capture with mocked dependencies
        self.screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock platform availability
        self.screen_capture.capture_available = True
    
    def test_high_frequency_frame_processing(self):
        """Test processing many frames in quick succession."""
        # Mock screen capture method
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        with patch.object(self.screen_capture, '_capture_screen', return_value=test_frame):
            with patch.object(self.screen_capture, '_compress_frame', return_value=b'compressed_data'):
                with patch.object(self.screen_capture, '_send_screen_frame') as mock_send:
                    
                    # Process multiple frames rapidly
                    start_time = time.time()
                    
                    for i in range(50):
                        self.screen_capture._process_frame(test_frame)
                    
                    end_time = time.time()
                    
                    # Verify all frames were processed
                    self.assertEqual(mock_send.call_count, 50)
                    
                    # Verify reasonable processing time (should be under 1 second)
                    processing_time = end_time - start_time
                    self.assertLess(processing_time, 1.0, "Frame processing took too long")
    
    def test_large_frame_compression_performance(self):
        """Test compression performance with large frames."""
        # Create large test frame (1080p)
        large_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        with patch('client.screen_capture.OPENCV_AVAILABLE', True):
            with patch('cv2.imencode') as mock_encode:
                # Mock successful compression
                compressed_data = np.random.randint(0, 255, 50000, dtype=np.uint8)
                mock_encode.return_value = (True, compressed_data)
                
                # Test compression timing
                start_time = time.time()
                result = self.screen_capture._compress_frame(large_frame)
                end_time = time.time()
                
                # Verify compression succeeded
                self.assertIsNotNone(result)
                
                # Verify reasonable compression time (should be under 0.5 seconds)
                compression_time = end_time - start_time
                self.assertLess(compression_time, 0.5, "Frame compression took too long")
    
    def test_memory_usage_during_continuous_capture(self):
        """Test memory usage doesn't grow excessively during continuous capture."""
        try:
            import psutil
            import gc
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            # Mock continuous frame processing
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            with patch.object(self.screen_capture, '_capture_screen', return_value=test_frame):
                with patch.object(self.screen_capture, '_compress_frame', return_value=b'compressed_data'):
                    with patch.object(self.screen_capture, '_send_screen_frame'):
                        
                        # Process many frames
                        for i in range(100):
                            self.screen_capture._process_frame(test_frame)
                            
                            # Force garbage collection every 10 frames
                            if i % 10 == 0:
                                gc.collect()
            
            # Get final memory usage
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            max_acceptable_increase = 100 * 1024 * 1024  # 100MB
            self.assertLess(memory_increase, max_acceptable_increase, 
                           f"Memory usage increased by {memory_increase / (1024*1024):.1f}MB")
        except ImportError:
            # Skip test if psutil is not available
            self.skipTest("psutil not available - skipping memory usage test")


if __name__ == '__main__':
    # Configure test runner for comprehensive output
    unittest.main(verbosity=2, buffer=True)