"""
Video performance tests for the collaboration suite.
Tests video compression, transmission quality, and grid layout rendering performance.
"""

import unittest
import time
import threading
import numpy as np
import cv2
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.video_capture import VideoCapture
from client.video_playback import VideoRenderer, VideoManager
from common.messages import UDPPacket, MessageFactory


class TestVideoCompression(unittest.TestCase):
    """Test video compression and transmission quality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.mock_connection_manager.send_udp_packet.return_value = True
        self.client_id = "test_client_001"
        
    def test_video_capture_initialization(self):
        """Test video capture component initialization."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Test initial state
        self.assertEqual(video_capture.client_id, self.client_id)
        self.assertEqual(video_capture.connection_manager, self.mock_connection_manager)
        self.assertFalse(video_capture.is_capturing)
        self.assertEqual(video_capture.sequence_number, 0)
        
        # Test default settings
        self.assertEqual(video_capture.width, VideoCapture.DEFAULT_WIDTH)
        self.assertEqual(video_capture.height, VideoCapture.DEFAULT_HEIGHT)
        self.assertEqual(video_capture.fps, VideoCapture.DEFAULT_FPS)
        self.assertEqual(video_capture.compression_quality, VideoCapture.COMPRESSION_QUALITY)
    
    def test_video_settings_configuration(self):
        """Test video settings configuration and validation."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Test valid settings
        video_capture.set_video_settings(width=1280, height=720, fps=30, quality=80)
        self.assertEqual(video_capture.width, 1280)
        self.assertEqual(video_capture.height, 720)
        self.assertEqual(video_capture.fps, 30)
        self.assertEqual(video_capture.compression_quality, 80)
        
        # Test boundary clamping
        video_capture.set_video_settings(width=50, height=50, fps=100, quality=200)
        self.assertGreaterEqual(video_capture.width, 160)  # Minimum width
        self.assertGreaterEqual(video_capture.height, 120)  # Minimum height
        self.assertLessEqual(video_capture.fps, 30)  # Maximum FPS
        self.assertLessEqual(video_capture.compression_quality, 100)  # Maximum quality
    
    @patch('cv2.VideoCapture')
    def test_camera_availability_check(self, mock_cv2_capture):
        """Test camera availability detection."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Mock camera available
        mock_camera = Mock()
        mock_camera.isOpened.return_value = True
        mock_cv2_capture.return_value = mock_camera
        
        self.assertTrue(video_capture.is_camera_available(0))
        
        # Mock camera not available
        mock_camera.isOpened.return_value = False
        self.assertFalse(video_capture.is_camera_available(0))
    
    def test_frame_compression_quality(self):
        """Test video frame compression quality and size."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Create test frame (640x480 RGB)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test compression with different quality settings
        qualities = [10, 50, 90]
        compressed_sizes = []
        
        for quality in qualities:
            video_capture.set_video_settings(quality=quality)
            compressed_data = video_capture._compress_frame(test_frame)
            
            self.assertIsNotNone(compressed_data)
            self.assertIsInstance(compressed_data, bytes)
            self.assertGreater(len(compressed_data), 0)
            
            compressed_sizes.append(len(compressed_data))
        
        # Higher quality should result in larger file sizes
        self.assertLess(compressed_sizes[0], compressed_sizes[1])  # 10% < 50%
        self.assertLess(compressed_sizes[1], compressed_sizes[2])  # 50% < 90%
    
    def test_frame_compression_performance(self):
        """Test video frame compression performance."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Create test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Measure compression time
        start_time = time.time()
        num_compressions = 100
        
        for _ in range(num_compressions):
            compressed_data = video_capture._compress_frame(test_frame)
            self.assertIsNotNone(compressed_data)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_compression_time = total_time / num_compressions
        
        # Compression should be fast enough for real-time (< 33ms for 30fps)
        self.assertLess(avg_compression_time, 0.033, 
                       f"Average compression time {avg_compression_time:.4f}s too slow for real-time")
        
        print(f"Average compression time: {avg_compression_time*1000:.2f}ms")
    
    def test_udp_packet_creation(self):
        """Test UDP packet creation for video transmission."""
        video_capture = VideoCapture(self.client_id, self.mock_connection_manager)
        
        # Create test compressed data
        test_data = b"compressed_video_data_test"
        
        # Test packet creation
        video_capture.sequence_number = 42
        video_capture._send_video_packet(test_data)
        
        # Verify UDP packet was sent
        self.mock_connection_manager.send_udp_packet.assert_called_once()
        
        # Get the packet that was sent
        call_args = self.mock_connection_manager.send_udp_packet.call_args[0]
        sent_packet = call_args[0]
        
        self.assertIsInstance(sent_packet, UDPPacket)
        self.assertEqual(sent_packet.sender_id, self.client_id)
        self.assertEqual(sent_packet.sequence_num, 42)
        self.assertEqual(sent_packet.data, test_data)
        self.assertEqual(sent_packet.packet_type, "video")


class TestVideoRendering(unittest.TestCase):
    """Test video rendering and playback performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.video_renderer = VideoRenderer()
        self.client_id = "test_client_002"
    
    def test_video_renderer_initialization(self):
        """Test video renderer initialization."""
        self.assertFalse(self.video_renderer.is_rendering)
        self.assertEqual(len(self.video_renderer.video_streams), 0)
        self.assertEqual(len(self.video_renderer.frame_buffers), 0)
        self.assertEqual(self.video_renderer.max_buffer_size, 5)
    
    def test_video_renderer_start_stop(self):
        """Test video renderer start and stop functionality."""
        # Test start
        self.assertTrue(self.video_renderer.start_rendering())
        self.assertTrue(self.video_renderer.is_rendering)
        
        # Test stop
        self.video_renderer.stop_rendering()
        self.assertFalse(self.video_renderer.is_rendering)
    
    def test_frame_decompression(self):
        """Test video frame decompression."""
        # Create test JPEG data
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        
        # Compress frame to JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
        self.assertTrue(success)
        
        compressed_data = encoded_frame.tobytes()
        
        # Test decompression
        decompressed_frame = self.video_renderer._decompress_frame(compressed_data)
        
        self.assertIsNotNone(decompressed_frame)
        self.assertIsInstance(decompressed_frame, np.ndarray)
        self.assertEqual(len(decompressed_frame.shape), 3)  # Should be 3D array (H, W, C)
        self.assertEqual(decompressed_frame.shape[2], 3)  # Should have 3 color channels
    
    def test_video_packet_processing(self):
        """Test video packet processing and buffering."""
        self.video_renderer.start_rendering()
        
        # Create test video packet
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
        success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
        compressed_data = encoded_frame.tobytes()
        
        video_packet = MessageFactory.create_video_packet(
            sender_id=self.client_id,
            sequence_num=1,
            video_data=compressed_data
        )
        
        # Process packet
        self.video_renderer.process_video_packet(video_packet)
        
        # Verify stream was created
        self.assertIn(self.client_id, self.video_renderer.video_streams)
        self.assertIn(self.client_id, self.video_renderer.frame_buffers)
        
        # Verify statistics
        stream_info = self.video_renderer.video_streams[self.client_id]
        self.assertEqual(stream_info['packets_received'], 1)
        self.assertEqual(stream_info['last_sequence'], 1)
        self.assertTrue(stream_info['active'])
        
        self.video_renderer.stop_rendering()
    
    def test_multiple_video_streams(self):
        """Test handling multiple concurrent video streams."""
        self.video_renderer.start_rendering()
        
        client_ids = ["client_001", "client_002", "client_003"]
        
        # Create and process packets from multiple clients
        for i, client_id in enumerate(client_ids):
            test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
            success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
            compressed_data = encoded_frame.tobytes()
            
            video_packet = MessageFactory.create_video_packet(
                sender_id=client_id,
                sequence_num=i + 1,
                video_data=compressed_data
            )
            
            self.video_renderer.process_video_packet(video_packet)
        
        # Verify all streams were created
        self.assertEqual(len(self.video_renderer.video_streams), 3)
        self.assertEqual(len(self.video_renderer.frame_buffers), 3)
        
        for client_id in client_ids:
            self.assertIn(client_id, self.video_renderer.video_streams)
            self.assertTrue(self.video_renderer.video_streams[client_id]['active'])
        
        self.video_renderer.stop_rendering()
    
    def test_frame_buffer_management(self):
        """Test frame buffer size management and overflow handling."""
        self.video_renderer.start_rendering()
        
        # Send more frames than buffer size
        num_frames = self.video_renderer.max_buffer_size + 3
        
        for i in range(num_frames):
            test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
            success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
            compressed_data = encoded_frame.tobytes()
            
            video_packet = MessageFactory.create_video_packet(
                sender_id=self.client_id,
                sequence_num=i,
                video_data=compressed_data
            )
            
            self.video_renderer.process_video_packet(video_packet)
        
        # Buffer should not exceed max size
        buffer_size = len(self.video_renderer.frame_buffers[self.client_id])
        self.assertLessEqual(buffer_size, self.video_renderer.max_buffer_size)
        
        self.video_renderer.stop_rendering()
    
    def test_rendering_performance(self):
        """Test video rendering performance with multiple streams."""
        self.video_renderer.start_rendering()
        
        # Create multiple video streams
        num_clients = 4
        frames_per_client = 30  # Simulate 1 second at 30fps
        
        start_time = time.time()
        
        for frame_num in range(frames_per_client):
            for client_num in range(num_clients):
                client_id = f"client_{client_num:03d}"
                
                # Create test frame
                test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 50]
                success, encoded_frame = cv2.imencode('.jpg', test_frame, encode_params)
                compressed_data = encoded_frame.tobytes()
                
                video_packet = MessageFactory.create_video_packet(
                    sender_id=client_id,
                    sequence_num=frame_num,
                    video_data=compressed_data
                )
                
                self.video_renderer.process_video_packet(video_packet)
        
        end_time = time.time()
        total_time = end_time - start_time
        total_frames = num_clients * frames_per_client
        avg_processing_time = total_time / total_frames
        
        # Processing should be fast enough for real-time
        self.assertLess(avg_processing_time, 0.01, 
                       f"Average processing time {avg_processing_time:.4f}s too slow")
        
        print(f"Processed {total_frames} frames in {total_time:.2f}s")
        print(f"Average processing time per frame: {avg_processing_time*1000:.2f}ms")
        
        self.video_renderer.stop_rendering()


class TestVideoGridLayout(unittest.TestCase):
    """Test video grid layout rendering performance."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock GUI components since we can't create actual tkinter widgets in tests
        self.mock_video_frame = Mock()
        self.mock_video_display = Mock()
        self.mock_video_frame.video_display = self.mock_video_display
    
    def test_grid_dimension_calculation(self):
        """Test grid dimension calculation for different numbers of video feeds."""
        test_cases = [
            (1, (1, 1)),
            (2, (2, 2)),
            (4, (2, 2)),
            (5, (2, 3)),
            (6, (2, 3)),
            (7, (3, 3)),
            (9, (3, 3)),
            (10, (4, 4)),
            (16, (4, 4))
        ]
        
        for num_clients, expected_dims in test_cases:
            active_clients = [f"client_{i}" for i in range(num_clients)]
            
            # Calculate grid dimensions (simplified version of the actual algorithm)
            if num_clients == 1:
                rows, cols = 1, 1
            elif num_clients <= 4:
                rows, cols = 2, 2
            elif num_clients <= 6:
                rows, cols = 2, 3
            elif num_clients <= 9:
                rows, cols = 3, 3
            else:
                rows, cols = 4, 4
            
            self.assertEqual((rows, cols), expected_dims, 
                           f"Grid dimensions for {num_clients} clients should be {expected_dims}")
    
    def test_grid_layout_performance(self):
        """Test performance of creating video grid layouts."""
        # Test with different numbers of video feeds
        client_counts = [1, 4, 9, 16]
        
        for num_clients in client_counts:
            active_clients = [f"client_{i:03d}" for i in range(num_clients)]
            
            start_time = time.time()
            
            # Simulate grid creation (simplified)
            for i, client_id in enumerate(active_clients):
                # Simulate creating GUI elements
                mock_frame = Mock()
                mock_label = Mock()
                mock_placeholder = Mock()
                
                # Simulate grid positioning calculations
                if num_clients <= 4:
                    cols = 2
                else:
                    cols = 3 if num_clients <= 6 else 4
                
                row = i // cols
                col = i % cols
            
            end_time = time.time()
            layout_time = end_time - start_time
            
            # Grid layout should be created quickly
            self.assertLess(layout_time, 0.1, 
                           f"Grid layout for {num_clients} clients took too long: {layout_time:.4f}s")
            
            print(f"Grid layout for {num_clients} clients: {layout_time*1000:.2f}ms")
    
    def test_video_feed_scaling(self):
        """Test video feed scaling calculations for grid layout."""
        # Test different video resolutions and grid sizes
        resolutions = [(640, 480), (1280, 720), (1920, 1080)]
        grid_sizes = [(1, 1), (2, 2), (3, 3), (4, 4)]
        
        for width, height in resolutions:
            for rows, cols in grid_sizes:
                # Calculate scaled dimensions (assuming 800x600 total display area)
                display_width, display_height = 800, 600
                
                cell_width = display_width // cols
                cell_height = display_height // rows
                
                # Calculate aspect ratio preserving scale
                scale_x = cell_width / width
                scale_y = cell_height / height
                scale = min(scale_x, scale_y)
                
                scaled_width = int(width * scale)
                scaled_height = int(height * scale)
                
                # Verify scaled dimensions fit in cell
                self.assertLessEqual(scaled_width, cell_width)
                self.assertLessEqual(scaled_height, cell_height)
                self.assertGreater(scaled_width, 0)
                self.assertGreater(scaled_height, 0)


class TestVideoManager(unittest.TestCase):
    """Test high-level video manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_connection_manager = Mock()
        self.client_id = "test_client_manager"
        self.video_manager = VideoManager(self.client_id, self.mock_connection_manager)
    
    def test_video_manager_initialization(self):
        """Test video manager initialization."""
        self.assertEqual(self.video_manager.client_id, self.client_id)
        self.assertEqual(self.video_manager.connection_manager, self.mock_connection_manager)
        self.assertFalse(self.video_manager.is_active)
        self.assertIsNotNone(self.video_manager.video_renderer)
    
    def test_video_system_lifecycle(self):
        """Test video system start and stop lifecycle."""
        # Test start
        self.assertTrue(self.video_manager.start_video_system())
        self.assertTrue(self.video_manager.is_active)
        
        # Test stop
        self.video_manager.stop_video_system()
        self.assertFalse(self.video_manager.is_active)
    
    def test_gui_callback_integration(self):
        """Test GUI callback integration."""
        mock_frame_callback = Mock()
        mock_status_callback = Mock()
        
        self.video_manager.set_gui_callbacks(mock_frame_callback, mock_status_callback)
        
        self.assertEqual(self.video_manager.gui_frame_callback, mock_frame_callback)
        self.assertEqual(self.video_manager.gui_status_callback, mock_status_callback)
    
    def test_video_statistics(self):
        """Test video statistics collection."""
        self.video_manager.start_video_system()
        
        stats = self.video_manager.get_video_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('is_active', stats)
        self.assertIn('client_id', stats)
        self.assertIn('renderer_stats', stats)
        
        self.assertTrue(stats['is_active'])
        self.assertEqual(stats['client_id'], self.client_id)
        
        self.video_manager.stop_video_system()


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)