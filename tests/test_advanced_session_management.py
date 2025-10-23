"""
Comprehensive system tests for advanced session management and error handling.
Tests multi-client scenarios, performance optimization, and graceful disconnection handling.
"""

import unittest
import threading
import time
import socket
import logging
from unittest.mock import Mock, patch, MagicMock
from server.session_manager import SessionManager
from server.network_handler import NetworkHandler
from server.performance_monitor import PerformanceMonitor, NetworkMetrics, SystemMetrics
from client.connection_manager import ConnectionManager, ConnectionStatus
from common.messages import MessageFactory, TCPMessage, UDPPacket

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestGracefulDisconnectionHandling(unittest.TestCase):
    """Test graceful disconnection handling and heartbeat mechanisms."""
    
    def setUp(self):
        """Set up test environment."""
        self.session_manager = SessionManager()
        self.mock_socket = Mock()
        
    def tearDown(self):
        """Clean up test environment."""
        pass
    
    def test_heartbeat_tracking(self):
        """Test client heartbeat tracking and timeout detection."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket, "test_user")
        
        # Verify client was added
        self.assertIsNotNone(client_id)
        client = self.session_manager.get_client(client_id)
        self.assertIsNotNone(client)
        self.assertEqual(client.username, "test_user")
        
        # Test heartbeat update
        initial_heartbeat = client.last_heartbeat
        time.sleep(0.1)  # Small delay
        
        success = self.session_manager.update_client_heartbeat(client_id)
        self.assertTrue(success)
        
        updated_client = self.session_manager.get_client(client_id)
        self.assertGreater(updated_client.last_heartbeat, initial_heartbeat)
    
    def test_inactive_client_detection(self):
        """Test detection of inactive clients based on heartbeat timeout."""
        # Add multiple clients
        client1_id = self.session_manager.add_client(Mock(), "user1")
        client2_id = self.session_manager.add_client(Mock(), "user2")
        
        # Update heartbeat for only one client
        self.session_manager.update_client_heartbeat(client1_id)
        
        # Simulate old heartbeat for client2 by manually setting it
        client2 = self.session_manager.get_client(client2_id)
        client2.last_heartbeat = time.time() - 35  # 35 seconds ago
        
        # Check for inactive clients with 30-second timeout
        inactive_clients = self.session_manager.get_inactive_clients(timeout_seconds=30)
        
        # Only client2 should be inactive
        self.assertIn(client2_id, inactive_clients)
        self.assertNotIn(client1_id, inactive_clients)
    
    def test_graceful_client_removal(self):
        """Test graceful client removal with proper notifications."""
        # Add a client
        client_id = self.session_manager.add_client(self.mock_socket, "test_user")
        
        # Verify client exists
        self.assertIsNotNone(self.session_manager.get_client(client_id))
        
        # Perform graceful removal
        success = self.session_manager.graceful_client_removal(client_id, "Test disconnection")
        self.assertTrue(success)
        
        # Verify client was removed
        self.assertIsNone(self.session_manager.get_client(client_id))
        
        # Check for pending broadcast messages
        broadcasts = self.session_manager.get_pending_broadcasts()
        self.assertGreater(len(broadcasts), 0)
        
        # Verify disconnect message was created
        disconnect_msg = broadcasts[-1]  # Last message should be disconnect
        self.assertEqual(disconnect_msg.msg_type, 'participant_left')
        self.assertEqual(disconnect_msg.data['client_id'], client_id)
        self.assertEqual(disconnect_msg.data['reason'], 'Test disconnection')
    
    def test_cleanup_inactive_clients(self):
        """Test automatic cleanup of inactive clients."""
        # Add multiple clients
        client1_id = self.session_manager.add_client(Mock(), "active_user")
        client2_id = self.session_manager.add_client(Mock(), "inactive_user")
        
        # Make client2 inactive
        client2 = self.session_manager.get_client(client2_id)
        client2.last_heartbeat = time.time() - 35  # 35 seconds ago
        
        # Cleanup inactive clients
        removed_clients = self.session_manager.cleanup_inactive_clients(timeout_seconds=30)
        
        # Verify only inactive client was removed
        self.assertIn(client2_id, removed_clients)
        self.assertNotIn(client1_id, removed_clients)
        
        # Verify client2 no longer exists
        self.assertIsNone(self.session_manager.get_client(client2_id))
        self.assertIsNotNone(self.session_manager.get_client(client1_id))


class TestPerformanceOptimization(unittest.TestCase):
    """Test adaptive performance optimization features."""
    
    def setUp(self):
        """Set up test environment."""
        self.performance_monitor = PerformanceMonitor(monitoring_interval=1.0)
        
    def tearDown(self):
        """Clean up test environment."""
        if self.performance_monitor.is_monitoring:
            self.performance_monitor.stop_monitoring()
    
    def test_performance_monitor_startup(self):
        """Test performance monitor initialization and startup."""
        # Test startup
        success = self.performance_monitor.start_monitoring()
        self.assertTrue(success)
        self.assertTrue(self.performance_monitor.is_monitoring)
        
        # Test duplicate startup
        success2 = self.performance_monitor.start_monitoring()
        self.assertTrue(success2)  # Should handle gracefully
        
        # Test shutdown
        self.performance_monitor.stop_monitoring()
        self.assertFalse(self.performance_monitor.is_monitoring)
    
    def test_adaptive_compression_quality_determination(self):
        """Test adaptive compression quality determination based on metrics."""
        compression_manager = self.performance_monitor.get_compression_manager()
        
        # Test high-quality conditions
        good_network = NetworkMetrics(
            latency_ms=20.0,
            packet_loss_rate=0.001,
            bandwidth_utilization=0.3,
            jitter_ms=2.0,
            timestamp=time.time()
        )
        
        good_system = SystemMetrics(
            cpu_usage_percent=30.0,
            memory_usage_percent=40.0,
            network_io_bytes_sent=1000,
            network_io_bytes_recv=1000,
            disk_io_read_bytes=500,
            disk_io_write_bytes=500,
            timestamp=time.time()
        )
        
        quality_update = compression_manager.adapt_quality_based_on_metrics(
            good_network, good_system
        )
        
        self.assertEqual(quality_update['video_quality'], 'high')
        self.assertEqual(quality_update['audio_quality'], 'high')
        
        # Test poor conditions
        poor_network = NetworkMetrics(
            latency_ms=250.0,
            packet_loss_rate=0.08,
            bandwidth_utilization=0.9,
            jitter_ms=60.0,
            timestamp=time.time()
        )
        
        poor_system = SystemMetrics(
            cpu_usage_percent=95.0,
            memory_usage_percent=85.0,
            network_io_bytes_sent=10000,
            network_io_bytes_recv=10000,
            disk_io_read_bytes=5000,
            disk_io_write_bytes=5000,
            timestamp=time.time()
        )
        
        quality_update = compression_manager.adapt_quality_based_on_metrics(
            poor_network, poor_system
        )
        
        # Should adapt to lower quality
        self.assertIn(quality_update['video_quality'], ['low', 'minimal'])
        self.assertIn(quality_update['audio_quality'], ['low', 'minimal'])
    
    def test_packet_loss_tracking(self):
        """Test packet loss tracking functionality."""
        client_id = "test_client_123"
        
        # Simulate perfect packet reception
        for i in range(10):
            self.performance_monitor.track_packet_loss(client_id, i, i)
        
        # Should have no packet loss
        loss_rate = self.performance_monitor.get_packet_loss_rate(client_id)
        self.assertEqual(loss_rate, 0.0)
        
        # Simulate some packet loss (skip sequence 5)
        self.performance_monitor.track_packet_loss(client_id, 10, 11)  # Skip 10, receive 11
        
        # Should detect packet loss
        loss_rate = self.performance_monitor.get_packet_loss_rate(client_id)
        self.assertGreater(loss_rate, 0.0)
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        # Start monitoring briefly to collect some data
        self.performance_monitor.start_monitoring()
        time.sleep(2)  # Let it collect a few samples
        
        summary = self.performance_monitor.get_performance_summary()
        
        # Verify summary structure
        self.assertIn('monitoring_active', summary)
        self.assertIn('current_video_quality', summary)
        self.assertIn('current_audio_quality', summary)
        self.assertTrue(summary['monitoring_active'])
        
        # Should have collected some samples
        if summary.get('samples_collected', 0) > 0:
            self.assertIn('avg_cpu_usage', summary)
            self.assertIn('current_cpu_usage', summary)


class TestMultiClientScenarios(unittest.TestCase):
    """Test multi-client scenarios and concurrent operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.session_manager = SessionManager()
        
    def tearDown(self):
        """Clean up test environment."""
        pass
    
    def test_concurrent_client_addition(self):
        """Test concurrent addition of multiple clients."""
        num_clients = 10
        client_ids = []
        threads = []
        
        def add_client(username):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, username)
            client_ids.append(client_id)
        
        # Create threads to add clients concurrently
        for i in range(num_clients):
            thread = threading.Thread(target=add_client, args=(f"user_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all clients were added
        self.assertEqual(len(client_ids), num_clients)
        self.assertEqual(len(set(client_ids)), num_clients)  # All unique
        
        # Verify session state
        all_clients = self.session_manager.get_all_clients()
        self.assertEqual(len(all_clients), num_clients)
    
    def test_concurrent_message_broadcasting(self):
        """Test concurrent message broadcasting to multiple clients."""
        # Add multiple clients
        client_ids = []
        for i in range(5):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, f"user_{i}")
            client_ids.append(client_id)
        
        # Create multiple chat messages concurrently
        messages = []
        threads = []
        
        def create_and_add_message(sender_id, text):
            message = MessageFactory.create_chat_message(sender_id, text)
            self.session_manager.add_chat_message(message)
            messages.append(message)
        
        # Send messages from different clients concurrently
        for i, client_id in enumerate(client_ids):
            thread = threading.Thread(
                target=create_and_add_message, 
                args=(client_id, f"Message from user {i}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all messages were added
        chat_history = self.session_manager.get_chat_history()
        self.assertGreaterEqual(len(chat_history), len(messages))
    
    def test_presenter_role_management_with_multiple_clients(self):
        """Test presenter role management with multiple clients."""
        # Add multiple clients
        client_ids = []
        for i in range(3):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, f"user_{i}")
            client_ids.append(client_id)
        
        # Test presenter role assignment
        success = self.session_manager.set_presenter(client_ids[0])
        self.assertTrue(success)
        
        current_presenter = self.session_manager.get_presenter()
        self.assertIsNotNone(current_presenter)
        self.assertEqual(current_presenter.client_id, client_ids[0])
        
        # Test presenter role switching
        success = self.session_manager.set_presenter(client_ids[1])
        self.assertTrue(success)
        
        # Verify old presenter is no longer presenter
        client_0 = self.session_manager.get_client(client_ids[0])
        self.assertFalse(client_0.is_presenter)
        
        # Verify new presenter
        current_presenter = self.session_manager.get_presenter()
        self.assertEqual(current_presenter.client_id, client_ids[1])
    
    def test_file_sharing_with_multiple_clients(self):
        """Test file sharing functionality with multiple clients."""
        # Add clients
        uploader_id = self.session_manager.add_client(Mock(), "uploader")
        downloader1_id = self.session_manager.add_client(Mock(), "downloader1")
        downloader2_id = self.session_manager.add_client(Mock(), "downloader2")
        
        # Create test file metadata
        from common.file_metadata import FileMetadata
        file_metadata = FileMetadata(
            filename="test_file.txt",
            filesize=1024,
            uploader_id=uploader_id
        )
        
        # Add file metadata
        success = self.session_manager.add_file_metadata(file_metadata)
        self.assertTrue(success)
        
        # Verify file is in shared files
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 1)
        self.assertEqual(shared_files[0].filename, "test_file.txt")
        
        # Test file metadata retrieval
        retrieved_metadata = self.session_manager.get_file_metadata(file_metadata.file_id)
        self.assertIsNotNone(retrieved_metadata)
        self.assertEqual(retrieved_metadata.filename, "test_file.txt")


class TestSystemPerformanceUnderLoad(unittest.TestCase):
    """Test system performance under various load conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.session_manager = SessionManager()
        
    def tearDown(self):
        """Clean up test environment."""
        pass
    
    def test_high_client_count_performance(self):
        """Test system performance with high number of clients."""
        num_clients = 50
        start_time = time.time()
        
        # Add many clients
        client_ids = []
        for i in range(num_clients):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, f"user_{i}")
            client_ids.append(client_id)
        
        add_time = time.time() - start_time
        
        # Verify all clients were added efficiently
        self.assertEqual(len(client_ids), num_clients)
        self.assertLess(add_time, 5.0)  # Should complete within 5 seconds
        
        # Test participant list generation performance
        start_time = time.time()
        participants = self.session_manager.get_participant_list()
        list_time = time.time() - start_time
        
        self.assertEqual(len(participants), num_clients)
        self.assertLess(list_time, 1.0)  # Should be fast
        
        # Test concurrent heartbeat updates
        start_time = time.time()
        threads = []
        
        def update_heartbeat(client_id):
            self.session_manager.update_client_heartbeat(client_id)
        
        for client_id in client_ids:
            thread = threading.Thread(target=update_heartbeat, args=(client_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        heartbeat_time = time.time() - start_time
        self.assertLess(heartbeat_time, 2.0)  # Should handle concurrent updates efficiently
    
    def test_chat_message_throughput(self):
        """Test chat message handling throughput."""
        # Add clients
        num_clients = 10
        client_ids = []
        for i in range(num_clients):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, f"user_{i}")
            client_ids.append(client_id)
        
        # Send many messages concurrently
        num_messages_per_client = 20
        start_time = time.time()
        threads = []
        
        def send_messages(client_id, count):
            for i in range(count):
                message = MessageFactory.create_chat_message(client_id, f"Message {i}")
                self.session_manager.add_chat_message(message)
        
        for client_id in client_ids:
            thread = threading.Thread(
                target=send_messages, 
                args=(client_id, num_messages_per_client)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        total_messages = num_clients * num_messages_per_client
        
        # Verify all messages were processed
        chat_history = self.session_manager.get_chat_history()
        self.assertGreaterEqual(len(chat_history), total_messages)
        
        # Calculate throughput
        throughput = total_messages / total_time
        logger.info(f"Chat message throughput: {throughput:.1f} messages/second")
        
        # Should handle at least 50 messages per second
        self.assertGreater(throughput, 50.0)
    
    def test_memory_usage_with_large_session(self):
        """Test memory usage with large session data."""
        import sys
        
        # Get initial memory usage
        initial_size = sys.getsizeof(self.session_manager)
        
        # Add many clients and messages
        num_clients = 100
        for i in range(num_clients):
            mock_socket = Mock()
            client_id = self.session_manager.add_client(mock_socket, f"user_{i}")
            
            # Add some chat messages for each client
            for j in range(10):
                message = MessageFactory.create_chat_message(client_id, f"Message {j} from user {i}")
                self.session_manager.add_chat_message(message)
        
        # Check memory usage growth
        final_size = sys.getsizeof(self.session_manager)
        memory_growth = final_size - initial_size
        
        logger.info(f"Memory growth with {num_clients} clients: {memory_growth} bytes")
        
        # Memory growth should be reasonable (less than 10MB for this test)
        self.assertLess(memory_growth, 10 * 1024 * 1024)


class TestNetworkConditionSimulation(unittest.TestCase):
    """Test system behavior under various simulated network conditions."""
    
    def setUp(self):
        """Set up test environment."""
        self.performance_monitor = PerformanceMonitor(monitoring_interval=0.5)
        
    def tearDown(self):
        """Clean up test environment."""
        if self.performance_monitor.is_monitoring:
            self.performance_monitor.stop_monitoring()
    
    def test_high_latency_adaptation(self):
        """Test system adaptation to high latency conditions."""
        compression_manager = self.performance_monitor.get_compression_manager()
        
        # Simulate high latency network
        high_latency_network = NetworkMetrics(
            latency_ms=300.0,  # Very high latency
            packet_loss_rate=0.02,
            bandwidth_utilization=0.6,
            jitter_ms=40.0,
            timestamp=time.time()
        )
        
        normal_system = SystemMetrics(
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            network_io_bytes_sent=5000,
            network_io_bytes_recv=5000,
            disk_io_read_bytes=1000,
            disk_io_write_bytes=1000,
            timestamp=time.time()
        )
        
        quality_update = compression_manager.adapt_quality_based_on_metrics(
            high_latency_network, normal_system
        )
        
        # Should adapt to lower quality due to high latency
        self.assertIn(quality_update['video_quality'], ['low', 'minimal'])
        self.assertIn(quality_update['audio_quality'], ['low', 'medium'])
    
    def test_high_packet_loss_adaptation(self):
        """Test system adaptation to high packet loss conditions."""
        compression_manager = self.performance_monitor.get_compression_manager()
        
        # Simulate high packet loss network
        high_loss_network = NetworkMetrics(
            latency_ms=50.0,
            packet_loss_rate=0.10,  # 10% packet loss
            bandwidth_utilization=0.4,
            jitter_ms=15.0,
            timestamp=time.time()
        )
        
        normal_system = SystemMetrics(
            cpu_usage_percent=40.0,
            memory_usage_percent=50.0,
            network_io_bytes_sent=3000,
            network_io_bytes_recv=3000,
            disk_io_read_bytes=800,
            disk_io_write_bytes=800,
            timestamp=time.time()
        )
        
        quality_update = compression_manager.adapt_quality_based_on_metrics(
            high_loss_network, normal_system
        )
        
        # Should adapt to minimal quality due to high packet loss
        self.assertEqual(quality_update['video_quality'], 'minimal')
        self.assertIn(quality_update['audio_quality'], ['low', 'minimal'])
    
    def test_high_cpu_usage_adaptation(self):
        """Test system adaptation to high CPU usage conditions."""
        compression_manager = self.performance_monitor.get_compression_manager()
        
        # Simulate normal network but high CPU usage
        normal_network = NetworkMetrics(
            latency_ms=30.0,
            packet_loss_rate=0.005,
            bandwidth_utilization=0.3,
            jitter_ms=5.0,
            timestamp=time.time()
        )
        
        high_cpu_system = SystemMetrics(
            cpu_usage_percent=95.0,  # Very high CPU usage
            memory_usage_percent=70.0,
            network_io_bytes_sent=2000,
            network_io_bytes_recv=2000,
            disk_io_read_bytes=500,
            disk_io_write_bytes=500,
            timestamp=time.time()
        )
        
        quality_update = compression_manager.adapt_quality_based_on_metrics(
            normal_network, high_cpu_system
        )
        
        # Should adapt to lower quality due to high CPU usage
        self.assertIn(quality_update['video_quality'], ['low', 'minimal'])
        self.assertIn(quality_update['audio_quality'], ['minimal', 'low'])


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)