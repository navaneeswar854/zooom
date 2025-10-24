"""
Unit tests for screen sharing components.
Tests screen capture, playback, message handling, and error scenarios.
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
from common.messages import TCPMessage, MessageType, MessageFactory, MessageValidator


class TestScreenCaptureUnit(unittest.TestCase):
    """Unit tests for screen capture functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.client_id = "test_client"
        self.mock_connection = Mock()
        self.screen_capture = ScreenCapture(self.client_id, self.mock_connection)
    
    def test_screen_capture_initialization(self):
        """Test screen capture initialization with different configurations."""
        # Test basic initialization
        self.assertEqual(self.screen_capture.client_id, self.client_id)
        self.assertEqual(self.screen_capture.connection_manager, self.mock_connection)
        self.assertFalse(self.screen_capture.is_capturing)
        self.assertEqual(self.screen_capture.fps, ScreenCapture.DEFAULT_FPS)
        self.assertEqual(self.screen_capture.compression_quality, ScreenCapture.COMPRESSION_QUALITY)
        
        # Test statistics initialization
        stats = self.screen_capture.get_capture_stats()
        self.assertEqual(stats['frames_captured'], 0)
        self.assertEqual(stats['frames_sent'], 0)
        self.assertEqual(stats['capture_errors'], 0)
        self.assertIsNone(stats['capture_start_time'])
    
    def test_capture_settings_configuration(self):
        """Test screen capture settings configuration."""
        # Test valid settings
        self.screen_capture.set_capture_settings(fps=5, quality=50)
        stats = self.screen_capture.get_capture_stats()
        self.assertEqual(stats['current_settings']['fps'], 5)
        self.assertEqual(stats['current_settings']['compression_quality'], 50)
        
        # Test boundary values
        self.screen_capture.set_capture_settings(fps=0, quality=0)  # Should clamp to minimum
        stats = self.screen_capture.get_capture_stats()
        self.assertGreaterEqual(stats['current_settings']['fps'], 1)
        self.assertGreaterEqual(stats['current_settings']['compression_quality'], 10)
        
        # Test maximum values
        self.screen_capture.set_capture_settings(fps=100, quality=200)  # Should clamp to maximum
        stats = self.screen_capture.get_capture_stats()
        self.assertLessEqual(stats['current_settings']['fps'], 15)
        self.assertLessEqual(stats['current_settings']['compression_quality'], 100)
        
        # Test region setting
        test_region = (100, 100, 800, 600)
        self.screen_capture.set_capture_settings(region=test_region)
        stats = self.screen_capture.get_capture_stats()
        self.assertEqual(stats['current_settings']['capture_region'], test_region)
    
    def test_frame_compression(self):
        """Test frame compression with different image formats and qualities."""
        # Create test frames with different properties
        test_frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),  # Standard RGB
            np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8),  # HD
            np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),  # Small
        ]
        
        for frame in test_frames:
            with patch('cv2.imencode') as mock_encode:
                # Mock successful compression
                compressed_data = np.random.randint(0, 255, 5000, dtype=np.uint8)
                mock_encode.return_value = (True, compressed_data)
                
                # Test compression
                result = self.screen_capture._compress_frame(frame)
                self.assertIsNotNone(result)
                self.assertIsInstance(result, bytes)
                
                # Verify OpenCV was called with correct parameters
                mock_encode.assert_called_once()
                call_args = mock_encode.call_args
                self.assertEqual(call_args[0][0], '.jpg')  # JPEG format
                self.assertIn(cv2.IMWRITE_JPEG_QUALITY, call_args[0][2])
    
    def test_frame_compression_quality_levels(self):
        """Test frame compression with different quality levels."""
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        quality_levels = [10, 30, 50, 70, 90]
        
        for quality in quality_levels:
            self.screen_capture.set_capture_settings(quality=quality)
            
            with patch('cv2.imencode') as mock_encode:
                # Mock compression with size inversely related to quality
                size = max(1000, 10000 - quality * 100)
                compressed_data = np.random.randint(0, 255, size, dtype=np.uint8)
                mock_encode.return_value = (True, compressed_data)
                
                result = self.screen_capture._compress_frame(test_frame)
                self.assertIsNotNone(result)
                
                # Verify quality parameter was passed
                call_args = mock_encode.call_args[0][2]
                quality_index = call_args.index(cv2.IMWRITE_JPEG_QUALITY)
                self.assertEqual(call_args[quality_index + 1], quality)
    
    def test_frame_compression_failure_handling(self):
        """Test frame compression failure scenarios."""
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test OpenCV compression failure
        with patch('cv2.imencode') as mock_encode:
            mock_encode.return_value = (False, None)  # Compression failed
            
            result = self.screen_capture._compress_frame(test_frame)
            self.assertIsNone(result)
        
        # Test exception during compression
        with patch('cv2.imencode', side_effect=Exception("Compression error")):
            result = self.screen_capture._compress_frame(test_frame)
            self.assertIsNone(result)
    
    def test_frame_resizing_algorithms(self):
        """Test frame resizing with various aspect ratios."""
        # Test cases: (input_size, expected_behavior)
        test_cases = [
            ((1920, 1080), "should_resize"),  # HD - exceeds max dimensions
            ((800, 600), "no_resize"),        # Fits within limits
            ((1600, 900), "should_resize"),   # 16:9 aspect ratio
            ((1024, 768), "should_resize"),   # 4:3 aspect ratio
            ((2560, 1440), "should_resize"),  # QHD - exceeds max dimensions
            ((400, 300), "no_resize"),        # Small frame
        ]
        
        for (width, height), expected in test_cases:
            test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            
            resized_frame = self.screen_capture._resize_frame_if_needed(test_frame)
            
            # Check that frame is valid
            self.assertIsInstance(resized_frame, np.ndarray)
            self.assertEqual(len(resized_frame.shape), 3)
            self.assertEqual(resized_frame.shape[2], 3)  # RGB channels
            
            # Check size constraints
            resized_height, resized_width = resized_frame.shape[:2]
            self.assertLessEqual(resized_width, ScreenCapture.MAX_WIDTH)
            self.assertLessEqual(resized_height, ScreenCapture.MAX_HEIGHT)
            
            # Check aspect ratio preservation
            original_aspect = width / height
            resized_aspect = resized_width / resized_height
            self.assertAlmostEqual(original_aspect, resized_aspect, places=2)
            
            # Check expected behavior
            if expected == "should_resize":
                self.assertTrue(resized_width < width or resized_height < height)
            elif expected == "no_resize":
                self.assertEqual(resized_width, width)
                self.assertEqual(resized_height, height)
    
    def test_screen_capture_start_stop(self):
        """Test screen capture start and stop functionality."""
        # Mock platform availability
        self.screen_capture.capture_available = True
        
        # Mock successful screen capture test
        with patch.object(self.screen_capture, '_test_screen_capture', return_value=(True, "Test passed")):
            # Test start capture
            success, message = self.screen_capture.start_capture()
            self.assertTrue(success)
            self.assertIn("started successfully", message)
            self.assertTrue(self.screen_capture.is_capturing)
            self.assertIsNotNone(self.screen_capture.capture_thread)
            
            # Test stop capture
            self.screen_capture.stop_capture()
            self.assertFalse(self.screen_capture.is_capturing)
    
    def test_screen_capture_error_scenarios(self):
        """Test various error scenarios during screen capture."""
        # Test platform unavailable
        self.screen_capture.capture_available = False
        success, message = self.screen_capture.start_capture()
        self.assertFalse(success)
        self.assertIn("not", message.lower())
        
        # Test capture already running
        self.screen_capture.capture_available = True
        self.screen_capture.is_capturing = True
        success, message = self.screen_capture.start_capture()
        self.assertTrue(success)
        self.assertIn("already", message.lower())
        
        # Reset state
        self.screen_capture.is_capturing = False
        
        # Test screen capture test failure
        with patch.object(self.screen_capture, '_test_screen_capture', return_value=(False, "Test failed")):
            success, message = self.screen_capture.start_capture()
            self.assertFalse(success)
            self.assertEqual(message, "Test failed")
    
    def test_capability_checking(self):
        """Test platform capability checking."""
        capability_info = self.screen_capture.get_capability_info()
        
        # Check required fields
        self.assertIn('platform', capability_info)
        self.assertIn('capture_available', capability_info)
        self.assertIn('dependencies', capability_info)
        
        # Check dependencies
        deps = capability_info['dependencies']
        self.assertIn('pyautogui', deps)
        self.assertIn('opencv', deps)
        
        # Test setup instructions
        instructions = self.screen_capture.get_setup_instructions()
        self.assertIsInstance(instructions, list)
        if not self.screen_capture.capture_available:
            self.assertGreater(len(instructions), 0)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.screen_capture.is_capturing:
            self.screen_capture.stop_capture()


class TestScreenPlaybackUnit(unittest.TestCase):
    """Unit tests for screen playback functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.client_id = "test_client"
        self.screen_playback = ScreenPlayback(self.client_id)
    
    def test_screen_playback_initialization(self):
        """Test screen playback initialization."""
        self.assertEqual(self.screen_playback.client_id, self.client_id)
        self.assertFalse(self.screen_playback.is_receiving)
        self.assertIsNone(self.screen_playback.current_presenter_id)
        self.assertIsNone(self.screen_playback.last_frame)
        
        # Test statistics initialization
        stats = self.screen_playback.get_playback_stats()
        self.assertEqual(stats['frames_received'], 0)
        self.assertEqual(stats['frames_displayed'], 0)
        self.assertEqual(stats['playback_errors'], 0)
    
    def test_frame_decompression(self):
        """Test frame decompression with various formats."""
        # Create test compressed frame data
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        with patch('cv2.imdecode', return_value=test_image) as mock_decode:
            # Test valid hex data
            test_data = b"fake_jpeg_data"
            hex_data = test_data.hex()
            
            result = self.screen_playback._decompress_frame(hex_data)
            
            self.assertIsNotNone(result)
            self.assertTrue(np.array_equal(result, test_image))
            mock_decode.assert_called_once()
            
            # Verify the data was converted correctly
            call_args = mock_decode.call_args[0][0]
            self.assertEqual(call_args.tobytes(), test_data)
    
    def test_frame_decompression_failure(self):
        """Test frame decompression failure scenarios."""
        # Test invalid hex data
        result = self.screen_playback._decompress_frame("invalid_hex_data")
        self.assertIsNone(result)
        
        # Test OpenCV decode failure
        with patch('cv2.imdecode', return_value=None):
            result = self.screen_playback._decompress_frame("deadbeef")
            self.assertIsNone(result)
        
        # Test exception during decompression
        with patch('cv2.imdecode', side_effect=Exception("Decode error")):
            result = self.screen_playback._decompress_frame("deadbeef")
            self.assertIsNone(result)
    
    def test_screen_message_processing(self):
        """Test processing of screen sharing messages."""
        self.screen_playback.start_receiving()
        
        # Track callbacks
        received_frames = []
        presenter_changes = []
        
        def frame_callback(frame, presenter_id):
            received_frames.append((frame, presenter_id))
        
        def presenter_callback(presenter_id):
            presenter_changes.append(presenter_id)
        
        self.screen_playback.set_frame_callback(frame_callback)
        self.screen_playback.set_presenter_change_callback(presenter_callback)
        
        # Create test message
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        with patch('cv2.imdecode', return_value=test_image):
            screen_message = TCPMessage(
                msg_type=MessageType.SCREEN_SHARE.value,
                sender_id="presenter_1",
                data={
                    'sequence_num': 1,
                    'frame_data': b"test_data".hex(),
                    'timestamp': time.time()
                }
            )
            
            # Process message
            success = self.screen_playback.process_screen_message(screen_message)
            self.assertTrue(success)
            
            # Verify callbacks were called
            self.assertEqual(len(received_frames), 1)
            self.assertEqual(received_frames[0][1], "presenter_1")
            self.assertEqual(len(presenter_changes), 1)
            self.assertEqual(presenter_changes[0], "presenter_1")
            
            # Verify state updates
            self.assertEqual(self.screen_playback.get_current_presenter(), "presenter_1")
    
    def test_presenter_change_handling(self):
        """Test presenter change detection and handling."""
        self.screen_playback.start_receiving()
        
        presenter_changes = []
        
        def presenter_callback(presenter_id):
            presenter_changes.append(presenter_id)
        
        self.screen_playback.set_presenter_change_callback(presenter_callback)
        
        # Simulate presenter changes
        self.screen_playback.handle_presenter_start("presenter_1")
        self.assertEqual(len(presenter_changes), 1)
        self.assertEqual(presenter_changes[0], "presenter_1")
        
        self.screen_playback.handle_presenter_stop("presenter_1")
        self.assertEqual(len(presenter_changes), 2)
        self.assertEqual(presenter_changes[1], None)
        
        # Verify state
        self.assertIsNone(self.screen_playback.get_current_presenter())
    
    def test_playback_statistics(self):
        """Test playback statistics tracking."""
        self.screen_playback.start_receiving()
        
        # Set up frame callback to ensure frames are displayed
        displayed_frames = []
        def frame_callback(frame, presenter_id):
            displayed_frames.append((frame, presenter_id))
        
        self.screen_playback.set_frame_callback(frame_callback)
        
        # Process multiple frames
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        with patch('cv2.imdecode', return_value=test_image):
            for i in range(5):
                screen_message = TCPMessage(
                    msg_type=MessageType.SCREEN_SHARE.value,
                    sender_id="presenter_1",
                    data={
                        'sequence_num': i,
                        'frame_data': f"test_data_{i}".encode().hex(),
                        'timestamp': time.time()
                    }
                )
                
                self.screen_playback.process_screen_message(screen_message)
        
        # Check statistics
        stats = self.screen_playback.get_playback_stats()
        self.assertEqual(stats['frames_received'], 5)
        self.assertEqual(stats['frames_displayed'], 5)
        self.assertGreater(stats['average_frame_size'], 0)
        self.assertIsNotNone(stats['last_frame_time'])
        
        # Verify callback was called
        self.assertEqual(len(displayed_frames), 5)
    
    def tearDown(self):
        """Clean up after tests."""
        self.screen_playback.stop_receiving()


class TestScreenSharingMessages(unittest.TestCase):
    """Unit tests for screen sharing message serialization/deserialization."""
    
    def test_presenter_request_message(self):
        """Test presenter request message creation and validation."""
        client_id = "test_client"
        
        # Create message
        message = MessageFactory.create_presenter_request_message(client_id)
        
        # Verify structure
        self.assertEqual(message.msg_type, MessageType.PRESENTER_REQUEST.value)
        self.assertEqual(message.sender_id, client_id)
        self.assertEqual(message.data, {})
        
        # Test validation
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(message)
        self.assertTrue(is_valid, f"Validation failed: {error_msg}")
    
    def test_presenter_granted_message(self):
        """Test presenter granted message creation and validation."""
        server_id = "server"
        presenter_id = "client_123"
        
        # Create message
        message = MessageFactory.create_presenter_granted_message(server_id, presenter_id)
        
        # Verify structure
        self.assertEqual(message.msg_type, MessageType.PRESENTER_GRANTED.value)
        self.assertEqual(message.sender_id, server_id)
        self.assertEqual(message.data['presenter_id'], presenter_id)
        
        # Test validation
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(message)
        self.assertTrue(is_valid, f"Validation failed: {error_msg}")
    
    def test_presenter_denied_message(self):
        """Test presenter denied message creation and validation."""
        server_id = "server"
        reason = "Another user is already presenting"
        
        # Create message
        message = MessageFactory.create_presenter_denied_message(server_id, reason)
        
        # Verify structure
        self.assertEqual(message.msg_type, MessageType.PRESENTER_DENIED.value)
        self.assertEqual(message.sender_id, server_id)
        self.assertEqual(message.data['reason'], reason)
        
        # Test validation
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(message)
        self.assertTrue(is_valid, f"Validation failed: {error_msg}")
    
    def test_screen_share_control_messages(self):
        """Test screen share start/stop message creation and validation."""
        client_id = "presenter_client"
        
        # Test start message
        start_message = MessageFactory.create_screen_share_start_message(client_id)
        self.assertEqual(start_message.msg_type, MessageType.SCREEN_SHARE_START.value)
        self.assertEqual(start_message.sender_id, client_id)
        self.assertEqual(start_message.data, {})
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(start_message)
        self.assertTrue(is_valid, f"Start message validation failed: {error_msg}")
        
        # Test stop message
        stop_message = MessageFactory.create_screen_share_stop_message(client_id)
        self.assertEqual(stop_message.msg_type, MessageType.SCREEN_SHARE_STOP.value)
        self.assertEqual(stop_message.sender_id, client_id)
        self.assertEqual(stop_message.data, {})
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(stop_message)
        self.assertTrue(is_valid, f"Stop message validation failed: {error_msg}")
    
    def test_screen_frame_message(self):
        """Test screen frame message creation and validation."""
        client_id = "presenter_client"
        
        # Create screen frame message
        frame_data = b"compressed_jpeg_data"
        message = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id=client_id,
            data={
                'sequence_num': 42,
                'frame_data': frame_data.hex(),
                'timestamp': time.time()
            }
        )
        
        # Test validation
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(message)
        self.assertTrue(is_valid, f"Frame message validation failed: {error_msg}")
        
        # Verify data integrity
        self.assertEqual(message.data['sequence_num'], 42)
        self.assertEqual(bytes.fromhex(message.data['frame_data']), frame_data)
        self.assertIsInstance(message.data['timestamp'], float)
    
    def test_message_validation_failures(self):
        """Test message validation with invalid data."""
        # Test presenter request with invalid data
        invalid_request = TCPMessage(
            msg_type=MessageType.PRESENTER_REQUEST.value,
            sender_id="client",
            data={'invalid': 'data'}  # Should be empty
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(invalid_request)
        self.assertFalse(is_valid)
        self.assertIn("empty data", error_msg)
        
        # Test presenter granted without presenter_id
        invalid_granted = TCPMessage(
            msg_type=MessageType.PRESENTER_GRANTED.value,
            sender_id="server",
            data={}  # Missing presenter_id
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(invalid_granted)
        self.assertFalse(is_valid)
        
        # Test screen frame without required fields
        invalid_frame = TCPMessage(
            msg_type=MessageType.SCREEN_SHARE.value,
            sender_id="client",
            data={'sequence_num': 1}  # Missing frame_data and timestamp
        )
        
        is_valid, error_msg = MessageValidator.validate_screen_sharing_message(invalid_frame)
        self.assertFalse(is_valid)


class TestScreenSharingErrorHandling(unittest.TestCase):
    """Unit tests for screen sharing error handling scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        self.client_id = "test_client"
        self.mock_connection = Mock()
        self.mock_gui = Mock()
        
        self.screen_manager = ScreenManager(
            self.client_id, 
            self.mock_connection, 
            self.mock_gui
        )
    
    def test_connection_manager_unavailable(self):
        """Test error handling when connection manager is unavailable."""
        # Create screen manager without connection manager
        screen_manager = ScreenManager(self.client_id, None, self.mock_gui)
        
        # Test presenter request
        screen_manager.request_presenter_role()
        
        # Verify error was shown to user
        self.mock_gui.show_error.assert_called()
        error_call = self.mock_gui.show_error.call_args
        self.assertIn("no connection manager", error_call[0][1].lower())
    
    def test_screen_capture_failure_handling(self):
        """Test error handling when screen capture fails."""
        # Mock presenter granted
        self.screen_manager.is_presenter = True
        
        # Mock screen capture capability check failure
        with patch.object(self.screen_manager.screen_capture, 'get_capability_info', 
                         return_value={'available': False, 'error_message': 'Screen capture failed'}):
            
            # Mock connection manager success
            self.mock_connection.start_screen_sharing.return_value = (True, "Started")
            
            # Attempt to start screen sharing
            self.screen_manager.handle_screen_share_confirmed()
            
            # Verify error was handled
            self.mock_gui.show_error.assert_called()
            error_call = self.mock_gui.show_error.call_args
            self.assertIn("Screen capture", error_call[0][1])
    
    def test_network_error_handling(self):
        """Test error handling for network-related errors."""
        # Mock connection manager failures
        self.mock_connection.request_presenter_role.return_value = (False, "Network error")
        
        # Test presenter request failure
        self.screen_manager.request_presenter_role()
        
        # Verify error was handled and shown to user
        self.mock_gui.show_error.assert_called()
        error_call = self.mock_gui.show_error.call_args
        self.assertIn("Network error", error_call[0][1])
    
    def test_gui_manager_unavailable(self):
        """Test error handling when GUI manager is unavailable."""
        # Create screen manager without GUI manager
        screen_manager = ScreenManager(self.client_id, self.mock_connection, None)
        
        # Test operations that would normally update GUI
        screen_manager.handle_presenter_granted()
        screen_manager.handle_presenter_denied("Test reason")
        
        # Should not crash even without GUI manager
        self.assertTrue(screen_manager.is_presenter)
    
    def test_concurrent_presenter_requests(self):
        """Test handling of concurrent presenter requests."""
        # Set request as pending
        self.screen_manager.presenter_request_pending = True
        
        # Try to make another request
        self.screen_manager.request_presenter_role()
        
        # Verify second request was rejected
        self.mock_gui.show_error.assert_called()
        error_call = self.mock_gui.show_error.call_args
        self.assertIn("already in progress", error_call[0][1])
    
    def test_invalid_message_handling(self):
        """Test handling of invalid screen sharing messages."""
        # Test with None message
        self.screen_manager.handle_screen_share_message(None)
        
        # Test with message missing required fields
        invalid_message = Mock()
        invalid_message.msg_type = None
        
        self.screen_manager.handle_screen_share_message(invalid_message)
        
        # Should handle gracefully without crashing
        # Verify error was logged (would need logging capture for full test)
    
    def test_cleanup_error_handling(self):
        """Test error handling during cleanup operations."""
        # Mock screen capture stop failure
        with patch.object(self.screen_manager.screen_capture, 'stop_capture', 
                         side_effect=Exception("Stop failed")):
            
            # Set sharing state
            self.screen_manager.is_sharing = True
            
            # Cleanup should handle the error gracefully
            self.screen_manager.cleanup()
            
            # State should still be reset
            self.assertFalse(self.screen_manager.is_sharing)
    
    def test_connection_loss_recovery(self):
        """Test handling of connection loss during screen sharing."""
        # Set up active screen sharing
        self.screen_manager.is_sharing = True
        self.screen_manager.is_presenter = True
        
        # Simulate connection loss
        self.screen_manager._on_connection_lost()
        
        # Verify error was shown to user
        self.mock_gui.show_error.assert_called()
        error_call = self.mock_gui.show_error.call_args
        self.assertIn("connection", error_call[0][1].lower())
        
        # Simulate connection restoration
        self.screen_manager._on_connection_restored()
        
        # Verify restoration message was shown
        restore_calls = [call for call in self.mock_gui.show_error.call_args_list 
                        if "restored" in call[0][1].lower()]
        self.assertGreater(len(restore_calls), 0)
    
    def tearDown(self):
        """Clean up after tests."""
        self.screen_manager.cleanup()


if __name__ == '__main__':
    unittest.main()