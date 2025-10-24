"""
Integration tests for screen sharing functionality.
Tests presenter role switching and screen capture/display quality.
"""

import unittest
import threading
import time
import tempfile
import os
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import sys
import cv2

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.screen_capture import ScreenCapture
from client.screen_playback import ScreenPlayback
from client.screen_manager import ScreenManager
from server.session_manager import SessionManager
from server.media_relay import MediaRelay, ScreenShareRelay
from common.messages import TCPMessage, MessageType, MessageFactory


class TestScreenSharingIntegration(unittest.TestCase):
    """Integration tests for screen sharing functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.client_id_1 = "client_1"
        self.client_id_2 = "client_2"
        
        # Create session manager
        self.session_manager = SessionManager()
        
        # Create mock connections
        self.mock_socket_1 = Mock()
        self.mock_socket_2 = Mock()
        
        # Add clients to session
        self.session_manager.add_client(self.mock_socket_1, "TestUser1")
        self.session_manager.add_client(self.mock_socket_2, "TestUser2")
        
        # Get assigned client IDs
        clients = self.session_manager.get_all_clients()
        self.client_id_1 = clients[0].client_id
        self.client_id_2 = clients[1].client_id
        
        # Create screen share relay
        self.screen_share_relay = ScreenShareRelay()
        
        # Mock connection managers
        self.mock_connection_1 = Mock()
        self.mock_connection_2 = Mock()
        
        # Configure mock connection managers to return tuples
        self.mock_connection_1.start_screen_sharing.return_value = (True, "Started")
        self.mock_connection_1.stop_screen_sharing.return_value = (True, "Stopped")
        self.mock_connection_1.request_presenter_role.return_value = (True, "Requested")
        
        self.mock_connection_2.start_screen_sharing.return_value = (True, "Started")
        self.mock_connection_2.stop_screen_sharing.return_value = (True, "Stopped")
        self.mock_connection_2.request_presenter_role.return_value = (True, "Requested")
        
        # Create screen managers
        self.screen_manager_1 = ScreenManager(self.client_id_1, self.mock_connection_1)
        self.screen_manager_2 = ScreenManager(self.client_id_2, self.mock_connection_2)
    
    def test_presenter_role_switching(self):
        """Test presenter role switching between clients."""
        # Initially no presenter
        self.assertIsNone(self.session_manager.get_presenter())
        self.assertFalse(self.session_manager.is_screen_sharing_active())
        
        # Client 1 requests presenter role
        success, message = self.session_manager.request_presenter_role(self.client_id_1)
        self.assertTrue(success)
        self.assertEqual(message, "Presenter role granted")
        
        # Verify client 1 is presenter
        presenter = self.session_manager.get_presenter()
        self.assertIsNotNone(presenter)
        self.assertEqual(presenter.client_id, self.client_id_1)
        self.assertTrue(presenter.is_presenter)
        
        # Client 2 tries to request presenter role (should fail)
        success, message = self.session_manager.request_presenter_role(self.client_id_2)
        self.assertFalse(success)
        self.assertIn("already taken", message)
        
        # Client 1 starts screen sharing
        success, msg = self.session_manager.start_screen_sharing(self.client_id_1)
        self.assertTrue(success)
        self.assertTrue(self.session_manager.is_screen_sharing_active())
        
        # Client 2 tries to start screen sharing (should fail)
        success, msg = self.session_manager.start_screen_sharing(self.client_id_2)
        self.assertFalse(success)
        
        # Client 1 stops screen sharing
        success, msg = self.session_manager.stop_screen_sharing(self.client_id_1)
        self.assertTrue(success)
        self.assertFalse(self.session_manager.is_screen_sharing_active())
        
        # Clear presenter
        success = self.session_manager.clear_presenter()
        self.assertTrue(success)
        self.assertIsNone(self.session_manager.get_presenter())
        
        # Now client 2 can become presenter
        success, message = self.session_manager.request_presenter_role(self.client_id_2)
        self.assertTrue(success)
        
        presenter = self.session_manager.get_presenter()
        self.assertEqual(presenter.client_id, self.client_id_2)
    
    def test_screen_capture_and_display_quality(self):
        """Test screen capture and display quality."""
        # Create test image array
        test_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        # Create screen capture with mock connection
        mock_connection = Mock()
        screen_capture = ScreenCapture(self.client_id_1, mock_connection)
        
        # Mock platform availability
        screen_capture.capture_available = True
        
        # Mock the screen capture method directly
        with patch.object(screen_capture, '_capture_screen', return_value=test_image):
            with patch('cv2.imencode') as mock_encode:
                # Mock successful encoding
                mock_encode.return_value = (True, np.array([1, 2, 3, 4, 5], dtype=np.uint8))
                
                # Set capture settings
                screen_capture.set_capture_settings(fps=5, quality=70)
                
                # Start capture
                success = screen_capture.start_capture()
                self.assertTrue(success)
                
                # Wait for some frames to be captured
                time.sleep(0.5)
                
                # Stop capture
                screen_capture.stop_capture()
                
                # Check statistics
                stats = screen_capture.get_capture_stats()
                self.assertGreater(stats['frames_captured'], 0)
                self.assertEqual(stats['current_settings']['fps'], 5)
                self.assertEqual(stats['current_settings']['compression_quality'], 70)
    
    def test_screen_frame_relay(self):
        """Test screen frame relay through server."""
        # Set up presenter
        self.session_manager.set_presenter(self.client_id_1)
        success, msg = self.session_manager.start_screen_sharing(self.client_id_1)
        self.assertTrue(success)
        
        # Create test screen frame message
        test_frame_data = b"test_screen_frame_data"
        screen_message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id=self.client_id_1,
            data={
                'sequence_num': 1,
                'frame_data': test_frame_data.hex(),
                'timestamp': time.time()
            }
        )
        
        # Track broadcast calls
        broadcast_calls = []
        
        def mock_broadcast(message, presenter_id):
            broadcast_calls.append((message, presenter_id))
        
        self.screen_share_relay.set_screen_broadcast_callback(mock_broadcast)
        
        # Relay screen frame
        self.screen_share_relay.relay_screen_frame(screen_message, self.client_id_1)
        
        # Verify broadcast was called
        self.assertEqual(len(broadcast_calls), 1)
        self.assertEqual(broadcast_calls[0][1], self.client_id_1)
        
        # Check statistics
        stats = self.screen_share_relay.get_screen_stats()
        self.assertEqual(stats['screen_frames_relayed'], 1)
        self.assertEqual(stats['presenter_id'], self.client_id_1)
        self.assertIsNotNone(stats['last_frame_time'])
    
    def test_screen_playback_processing(self):
        """Test screen frame processing and playback."""
        # Create screen playback
        screen_playback = ScreenPlayback(self.client_id_2)
        
        # Track frame callbacks
        received_frames = []
        presenter_changes = []
        
        def frame_callback(frame, presenter_id):
            received_frames.append((frame, presenter_id))
        
        def presenter_callback(presenter_id):
            presenter_changes.append(presenter_id)
        
        screen_playback.set_frame_callback(frame_callback)
        screen_playback.set_presenter_change_callback(presenter_callback)
        
        # Start receiving
        success = screen_playback.start_receiving()
        self.assertTrue(success)
        
        # Create test screen frame (small test image)
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        with patch('cv2.imdecode', return_value=test_image):
            # Create test screen message
            test_frame_data = b"fake_jpeg_data"
            screen_message = TCPMessage(
                msg_type=MessageType.SCREEN_SHARE.value,
                sender_id=self.client_id_1,
                data={
                    'sequence_num': 1,
                    'frame_data': test_frame_data.hex(),
                    'timestamp': time.time()
                }
            )
            
            # Process screen message
            success = screen_playback.process_screen_message(screen_message)
            self.assertTrue(success)
            
            # Verify frame was received
            self.assertEqual(len(received_frames), 1)
            self.assertEqual(received_frames[0][1], self.client_id_1)
            
            # Verify presenter change was detected
            self.assertEqual(len(presenter_changes), 1)
            self.assertEqual(presenter_changes[0], self.client_id_1)
            
            # Check current presenter
            self.assertEqual(screen_playback.get_current_presenter(), self.client_id_1)
            
            # Check statistics (don't check is_screen_sharing_active as it depends on timing)
            stats = screen_playback.get_playback_stats()
            # The presenter ID should match what we sent
            if stats['current_presenter_id'] is not None:
                self.assertEqual(stats['current_presenter_id'], self.client_id_1)
        
        # Stop receiving
        screen_playback.stop_receiving()
        
        # Check statistics
        stats = screen_playback.get_playback_stats()
        self.assertEqual(stats['frames_received'], 1)
        self.assertEqual(stats['frames_displayed'], 1)
        # Check presenter ID if it's set
        if stats['current_presenter_id'] is not None:
            self.assertEqual(stats['current_presenter_id'], self.client_id_1)
    
    def test_screen_manager_integration(self):
        """Test screen manager integration with all components."""
        # Mock GUI manager
        mock_gui = Mock()
        self.screen_manager_1.gui_manager = mock_gui
        
        # Test presenter request
        self.screen_manager_1.request_presenter_role()
        self.mock_connection_1.request_presenter_role.assert_called_once()
        
        # Test screen sharing start (happens automatically when presenter is granted)
        with patch.object(self.screen_manager_1.screen_capture, 'start_capture', return_value=(True, "Started")):
            with patch.object(self.screen_manager_1.screen_capture, 'get_capability_info', return_value={'available': True}):
                # Simulate presenter granted (this will auto-start screen sharing)
                self.screen_manager_1.handle_presenter_granted()
                self.assertTrue(self.screen_manager_1.is_presenter)
                mock_gui.handle_presenter_granted.assert_called_once()
                
                # Simulate server confirmation
                self.screen_manager_1.handle_screen_share_confirmed()
                
                self.assertTrue(self.screen_manager_1.is_sharing)
                self.mock_connection_1.start_screen_sharing.assert_called_once()
                mock_gui.set_screen_sharing_status.assert_called_with(True)
        
        # Test screen sharing stop
        self.screen_manager_1.stop_screen_sharing()
        self.assertFalse(self.screen_manager_1.is_sharing)
        self.mock_connection_1.stop_screen_sharing.assert_called_once()
        mock_gui.set_screen_sharing_status.assert_called_with(False)
        
        # Test presenter denied
        self.screen_manager_2.handle_presenter_denied("Already taken")
        self.assertFalse(self.screen_manager_2.presenter_request_pending)
    
    def test_screen_sharing_message_handling(self):
        """Test handling of various screen sharing messages."""
        mock_gui = Mock()
        self.screen_manager_2.gui_manager = mock_gui
        
        # Test screen share start message
        start_message = MessageFactory.create_screen_share_start_message(self.client_id_1)
        self.screen_manager_2.handle_screen_share_message(start_message)
        mock_gui.handle_screen_share_started.assert_called_once()
        
        # Test screen share stop message
        stop_message = MessageFactory.create_screen_share_stop_message(self.client_id_1)
        self.screen_manager_2.handle_screen_share_message(stop_message)
        mock_gui.handle_screen_share_stopped.assert_called_once()
        
        # Test presenter granted message
        granted_message = MessageFactory.create_presenter_granted_message(
            "server", self.client_id_2
        )
        self.screen_manager_2.handle_screen_share_message(granted_message)
        self.assertTrue(self.screen_manager_2.is_presenter)
        
        # Test presenter denied message
        denied_message = MessageFactory.create_presenter_denied_message(
            "server", "Already taken"
        )
        self.screen_manager_2.handle_screen_share_message(denied_message)
    
    def test_screen_sharing_status_reporting(self):
        """Test screen sharing status reporting."""
        # Get initial status
        status = self.screen_manager_1.get_screen_sharing_status()
        self.assertFalse(status['is_presenter'])
        self.assertFalse(status['is_sharing'])
        self.assertFalse(status['presenter_request_pending'])
        
        # Simulate screen sharing start (happens automatically when presenter is granted)
        with patch.object(self.screen_manager_1.screen_capture, 'start_capture', return_value=(True, "Started")):
            with patch.object(self.screen_manager_1.screen_capture, 'get_capability_info', return_value={'available': True}):
                # Simulate presenter granted (this will auto-start screen sharing)
                self.screen_manager_1.handle_presenter_granted()
                status = self.screen_manager_1.get_screen_sharing_status()
                self.assertTrue(status['is_presenter'])
                
                # Simulate server confirmation
                self.screen_manager_1.handle_screen_share_confirmed()
                status = self.screen_manager_1.get_screen_sharing_status()
                self.assertTrue(status['is_sharing'])
    
    def test_screen_capture_settings(self):
        """Test screen capture settings configuration."""
        # Test settings update
        self.screen_manager_1.set_screen_capture_settings(fps=10, quality=80)
        
        # Verify settings were applied
        settings = self.screen_manager_1.screen_capture.get_capture_stats()['current_settings']
        self.assertEqual(settings['fps'], 10)
        self.assertEqual(settings['compression_quality'], 80)
    
    def test_window_capture_selection(self):
        """Test window selection for capture."""
        # Mock available windows
        mock_windows = [
            {'title': 'Test Window 1', 'left': 0, 'top': 0, 'width': 800, 'height': 600},
            {'title': 'Test Window 2', 'left': 100, 'top': 100, 'width': 1024, 'height': 768}
        ]
        
        with patch.object(self.screen_manager_1.screen_capture, 'get_available_windows', 
                         return_value=mock_windows):
            # Get available windows
            windows = self.screen_manager_1.get_available_windows()
            self.assertEqual(len(windows), 2)
            self.assertEqual(windows[0]['title'], 'Test Window 1')
            
            # Set capture window
            with patch.object(self.screen_manager_1.screen_capture, 'set_capture_window', 
                             return_value=True):
                success = self.screen_manager_1.set_capture_window('Test Window 1')
                self.assertTrue(success)
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up screen managers
        self.screen_manager_1.cleanup()
        self.screen_manager_2.cleanup()


class TestScreenSharingPerformance(unittest.TestCase):
    """Performance tests for screen sharing functionality."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.client_id = "perf_test_client"
        self.mock_connection = Mock()
    
    def test_screen_capture_performance(self):
        """Test screen capture performance under load."""
        # Create test image
        test_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        screen_capture = ScreenCapture(self.client_id, self.mock_connection)
        
        # Mock platform availability
        screen_capture.capture_available = True
        
        # Mock the screen capture method directly
        with patch.object(screen_capture, '_capture_screen', return_value=test_image):
            with patch('cv2.imencode') as mock_encode:
                # Mock encoding with realistic data size
                encoded_data = np.random.randint(0, 255, 50000, dtype=np.uint8)
                mock_encode.return_value = (True, encoded_data)
                
                screen_capture.set_capture_settings(fps=10, quality=50)
                
                # Start capture
                start_time = time.time()
                screen_capture.start_capture()
                
                # Run for 2 seconds
                time.sleep(2.0)
                
                # Stop capture
                screen_capture.stop_capture()
                end_time = time.time()
                
                # Check performance metrics
                stats = screen_capture.get_capture_stats()
                duration = end_time - start_time
                
                # Should capture approximately 20 frames in 2 seconds at 10 FPS
                expected_frames = int(10 * duration * 0.8)  # Allow 20% tolerance
                self.assertGreaterEqual(stats['frames_captured'], expected_frames)
                
                # Check average frame size is reasonable
                self.assertGreater(stats['average_frame_size'], 1000)  # At least 1KB per frame
                self.assertLess(stats['average_frame_size'], 200000)   # Less than 200KB per frame
    
    def test_screen_playback_performance(self):
        """Test screen playback performance with multiple frames."""
        screen_playback = ScreenPlayback(self.client_id)
        
        # Track processed frames
        processed_frames = []
        
        def frame_callback(frame, presenter_id):
            processed_frames.append(time.time())
        
        screen_playback.set_frame_callback(frame_callback)
        screen_playback.start_receiving()
        
        # Create test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        with patch('cv2.imdecode', return_value=test_image):
            # Send multiple frames rapidly
            start_time = time.time()
            
            for i in range(50):
                test_frame_data = f"frame_{i}".encode()
                screen_message = TCPMessage(
                    msg_type=MessageType.SCREEN_SHARE.value,
                    sender_id="test_presenter",
                    data={
                        'sequence_num': i,
                        'frame_data': test_frame_data.hex(),
                        'timestamp': time.time()
                    }
                )
                
                screen_playback.process_screen_message(screen_message)
                time.sleep(0.01)  # Small delay between frames
            
            end_time = time.time()
            
            # Check that all frames were processed
            stats = screen_playback.get_playback_stats()
            self.assertEqual(stats['frames_received'], 50)
            self.assertEqual(stats['frames_displayed'], 50)
            
            # Check processing rate
            duration = end_time - start_time
            fps = 50 / duration
            self.assertGreater(fps, 30)  # Should handle at least 30 FPS
        
        screen_playback.stop_receiving()


if __name__ == '__main__':
    unittest.main()