"""
System validation tests for the LAN Collaboration Suite.
Comprehensive tests for system reliability, performance, and edge cases.
"""

import unittest
import sys
import os
import threading
import time
import tempfile
import socket
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.session_manager import SessionManager
from server.network_handler import NetworkHandler
from server.media_relay import MediaRelay, AudioMixer, VideoBroadcaster
from client.connection_manager import ConnectionManager
from common.messages import TCPMessage, UDPPacket, MessageType, MessageFactory
from common.networking import TCPServer, UDPServer, TCPClient, UDPClient
from common.platform_utils import PLATFORM_INFO, NetworkUtils


class TestSystemReliability(unittest.TestCase):
    """Test system reliability under various conditions."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_manager = SessionManager(file_storage_dir=self.temp_dir)
    
    def tearDown(self):
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_graceful_degradation(self):
        """Test system behavior when components fail gracefully."""
        # Test session manager with invalid operations
        invalid_operations = [
            lambda: self.session_manager.remove_client("nonexistent"),
            lambda: self.session_manager.set_presenter("nonexistent"),
            lambda: self.session_manager.update_client_media_status("nonexistent", True, True),
            lambda: self.session_manager.get_file_path("nonexistent")
        ]
        
        for operation in invalid_operations:
            try:
                result = operation()
                # Should return False or None, not raise exception
                self.assertIn(result, [False, None])
            except Exception as e:
                self.fail(f"Operation should fail gracefully, not raise exception: {e}")
    
    def test_memory_management(self):
        """Test memory management under load."""
        import gc
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create and destroy many objects
        for iteration in range(10):
            clients = []
            
            # Add many clients
            for i in range(20):
                client_id = self.session_manager.add_client(Mock(), f"Client{i}")
                clients.append(client_id)
            
            # Send many messages
            for i in range(50):
                sender_id = clients[i % len(clients)]
                message = MessageFactory.create_chat_message(sender_id, f"Message {i}")
                self.session_manager.add_chat_message(message)
            
            # Remove all clients
            for client_id in clients:
                self.session_manager.remove_client(client_id)
            
            # Force garbage collection
            gc.collect()
        
        # Check final memory usage
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow excessively
        memory_growth = final_objects - initial_objects
        self.assertLess(memory_growth, 1000, f"Excessive memory growth: {memory_growth} objects")
    
    def test_thread_safety(self):
        """Test thread safety of core components."""
        results = []
        errors = []
        
        def client_operations(thread_id):
            try:
                # Add client
                client_id = self.session_manager.add_client(Mock(), f"ThreadClient{thread_id}")
                results.append(f"added_{thread_id}")
                
                # Send messages
                for i in range(10):
                    message = MessageFactory.create_chat_message(client_id, f"Thread {thread_id} Message {i}")
                    self.session_manager.add_chat_message(message)
                
                # Update media status
                self.session_manager.update_client_media_status(
                    client_id, video_enabled=True, audio_enabled=True
                )
                
                # Remove client
                self.session_manager.remove_client(client_id)
                results.append(f"removed_{thread_id}")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Run multiple threads concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=client_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        if errors:
            self.fail(f"Thread safety errors: {errors}")
        
        # Should have add and remove for each thread
        self.assertEqual(len(results), 20)  # 10 adds + 10 removes
    
    def test_resource_cleanup(self):
        """Test proper resource cleanup."""
        # Create resources
        client_ids = []
        for i in range(5):
            client_id = self.session_manager.add_client(Mock(), f"CleanupClient{i}")
            client_ids.append(client_id)
        
        # Create files
        test_files = []
        for i in range(3):
            test_file = Path(self.temp_dir) / f"test_file_{i}.txt"
            test_file.write_text(f"Test content {i}")
            test_files.append(test_file)
        
        # Verify resources exist
        self.assertEqual(len(self.session_manager.get_participant_list()), 5)
        for test_file in test_files:
            self.assertTrue(test_file.exists())
        
        # Cleanup clients
        for client_id in client_ids:
            self.session_manager.remove_client(client_id)
        
        # Verify cleanup
        self.assertEqual(len(self.session_manager.get_participant_list()), 0)
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # Test recovery from invalid data
        invalid_messages = [
            {"invalid": "structure"},
            None,
            "",
            {"msg_type": "invalid", "sender_id": "", "data": {}}
        ]
        
        for invalid_msg in invalid_messages:
            try:
                if isinstance(invalid_msg, dict):
                    # Try to create message from invalid data
                    message = TCPMessage(**invalid_msg)
                    # Should handle gracefully
                else:
                    # Skip non-dict invalid messages
                    continue
            except Exception:
                # Expected to fail, should not crash system
                pass
        
        # System should still be functional
        client_id = self.session_manager.add_client(Mock(), "RecoveryTest")
        self.assertIsNotNone(client_id)
        
        valid_message = MessageFactory.create_chat_message(client_id, "Recovery test message")
        self.session_manager.add_chat_message(valid_message)
        
        chat_history = self.session_manager.get_chat_history()
        self.assertGreater(len(chat_history), 0)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests."""
    
    def setUp(self):
        self.session_manager = SessionManager()
    
    def test_client_scaling(self):
        """Test performance with increasing number of clients."""
        client_counts = [10, 50, 100, 200]
        performance_results = {}
        
        for count in client_counts:
            start_time = time.time()
            
            # Add clients
            client_ids = []
            for i in range(count):
                client_id = self.session_manager.add_client(Mock(), f"ScaleClient{i}")
                client_ids.append(client_id)
            
            add_time = time.time() - start_time
            
            # Test operations with all clients
            start_time = time.time()
            
            # Get participant list
            participants = self.session_manager.get_participant_list()
            self.assertEqual(len(participants), count)
            
            # Send messages from random clients
            for i in range(min(100, count)):
                sender_id = client_ids[i % len(client_ids)]
                message = MessageFactory.create_chat_message(sender_id, f"Scale test message {i}")
                self.session_manager.add_chat_message(message)
            
            operation_time = time.time() - start_time
            
            # Cleanup
            start_time = time.time()
            for client_id in client_ids:
                self.session_manager.remove_client(client_id)
            cleanup_time = time.time() - start_time
            
            performance_results[count] = {
                'add_time': add_time,
                'operation_time': operation_time,
                'cleanup_time': cleanup_time
            }
        
        # Verify performance doesn't degrade too much with scale
        for count in client_counts:
            results = performance_results[count]
            
            # Performance should be reasonable
            self.assertLess(results['add_time'], count * 0.01, 
                          f"Client addition too slow for {count} clients")
            self.assertLess(results['operation_time'], 5.0, 
                          f"Operations too slow for {count} clients")
            self.assertLess(results['cleanup_time'], count * 0.01, 
                          f"Cleanup too slow for {count} clients")
    
    def test_message_throughput(self):
        """Test message processing throughput."""
        # Add test clients
        client_ids = []
        for i in range(10):
            client_id = self.session_manager.add_client(Mock(), f"ThroughputClient{i}")
            client_ids.append(client_id)
        
        # Test different message volumes
        message_counts = [100, 500, 1000, 2000]
        
        for count in message_counts:
            start_time = time.time()
            
            # Send messages
            for i in range(count):
                sender_id = client_ids[i % len(client_ids)]
                message = MessageFactory.create_chat_message(sender_id, f"Throughput test {i}")
                self.session_manager.add_chat_message(message)
            
            processing_time = time.time() - start_time
            throughput = count / processing_time
            
            # Should process at least 100 messages per second
            self.assertGreater(throughput, 100, 
                             f"Message throughput too low: {throughput:.1f} msg/sec for {count} messages")
    
    def test_concurrent_load(self):
        """Test performance under concurrent load."""
        results = {}
        errors = []
        
        def concurrent_operations(worker_id, operation_count):
            try:
                start_time = time.time()
                
                # Add client
                client_id = self.session_manager.add_client(Mock(), f"ConcurrentClient{worker_id}")
                
                # Perform operations
                for i in range(operation_count):
                    # Send message
                    message = MessageFactory.create_chat_message(
                        client_id, f"Worker {worker_id} Message {i}"
                    )
                    self.session_manager.add_chat_message(message)
                    
                    # Update media status
                    self.session_manager.update_client_media_status(
                        client_id, video_enabled=(i % 2 == 0), audio_enabled=True
                    )
                
                # Remove client
                self.session_manager.remove_client(client_id)
                
                end_time = time.time()
                results[worker_id] = end_time - start_time
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(20):
                future = executor.submit(concurrent_operations, i, 50)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures, timeout=30):
                try:
                    future.result()
                except Exception as e:
                    errors.append(f"Future error: {e}")
        
        # Check results
        if errors:
            self.fail(f"Concurrent load errors: {errors}")
        
        # All workers should complete in reasonable time
        max_time = max(results.values())
        avg_time = sum(results.values()) / len(results)
        
        self.assertLess(max_time, 10.0, f"Maximum worker time too high: {max_time:.2f}s")
        self.assertLess(avg_time, 5.0, f"Average worker time too high: {avg_time:.2f}s")


class TestNetworkingComponents(unittest.TestCase):
    """Test networking components in isolation."""
    
    def test_tcp_socket_operations(self):
        """Test TCP socket operations."""
        from common.networking import TCPSocket
        
        # Test socket creation
        tcp_socket = TCPSocket("localhost", 0)  # Use port 0 for auto-assignment
        socket_obj = tcp_socket.create_socket()
        
        self.assertIsNotNone(socket_obj)
        
        # Test socket configuration
        try:
            socket_obj.bind(("localhost", 0))
            actual_port = socket_obj.getsockname()[1]
            self.assertGreater(actual_port, 0)
        finally:
            socket_obj.close()
    
    def test_udp_socket_operations(self):
        """Test UDP socket operations."""
        from common.networking import UDPSocket
        
        # Test socket creation
        udp_socket = UDPSocket("localhost", 0)
        socket_obj = udp_socket.create_socket()
        
        self.assertIsNotNone(socket_obj)
        
        # Test socket configuration
        try:
            socket_obj.bind(("localhost", 0))
            actual_port = socket_obj.getsockname()[1]
            self.assertGreater(actual_port, 0)
        finally:
            socket_obj.close()
    
    def test_message_serialization_performance(self):
        """Test message serialization performance."""
        # Test TCP message serialization
        tcp_message = MessageFactory.create_chat_message("client1", "Performance test message")
        
        start_time = time.time()
        for _ in range(1000):
            serialized = tcp_message.serialize()
            deserialized = TCPMessage.deserialize(serialized)
        tcp_time = time.time() - start_time
        
        # Test UDP packet serialization
        udp_packet = MessageFactory.create_audio_packet("client1", 42, b"audio_data" * 100)
        
        start_time = time.time()
        for _ in range(1000):
            serialized = udp_packet.serialize()
            deserialized = UDPPacket.deserialize(serialized)
        udp_time = time.time() - start_time
        
        # Performance should be reasonable
        self.assertLess(tcp_time, 1.0, f"TCP serialization too slow: {tcp_time:.3f}s")
        self.assertLess(udp_time, 1.0, f"UDP serialization too slow: {udp_time:.3f}s")
    
    def test_network_error_handling(self):
        """Test network error handling."""
        # Test connection to non-existent server
        try:
            from common.networking import TCPClient
            client = TCPClient("192.0.2.1", 12345)  # RFC 5737 test address
            connected = client.connect()
            self.assertFalse(connected)
        except Exception:
            # Should handle connection errors gracefully
            pass
        
        # Test invalid message deserialization
        invalid_data = [
            b"invalid json data",
            b"",
            b"null",
            b'{"incomplete": "json"'
        ]
        
        for data in invalid_data:
            try:
                TCPMessage.deserialize(data)
                self.fail("Should have raised exception for invalid data")
            except (ValueError, json.JSONDecodeError):
                # Expected behavior
                pass


class TestMediaComponents(unittest.TestCase):
    """Test media processing components."""
    
    def test_audio_mixer_functionality(self):
        """Test audio mixer component."""
        mixer = AudioMixer()
        
        # Test mixer initialization
        self.assertFalse(mixer.is_mixing)
        self.assertEqual(mixer.stats['total_mixed_packets'], 0)
        
        # Test audio stream management
        test_packet = MessageFactory.create_audio_packet("client1", 0, b"test_audio_data")
        mixer.add_audio_stream("client1", test_packet)
        
        # Verify stream was added
        self.assertIn("client1", mixer.client_buffers)
        
        # Test stream removal
        mixer.remove_audio_stream("client1")
        self.assertNotIn("client1", mixer.client_buffers)
    
    def test_video_broadcaster_functionality(self):
        """Test video broadcaster component."""
        broadcaster = VideoBroadcaster()
        
        # Test broadcaster initialization
        self.assertEqual(broadcaster.stats['video_packets_relayed'], 0)
        self.assertEqual(broadcaster.stats['active_video_clients'], 0)
        
        # Test video stream management
        test_packet = MessageFactory.create_video_packet("client1", 0, b"test_video_data")
        broadcaster.add_video_stream("client1", test_packet)
        
        # Verify stream statistics
        self.assertEqual(broadcaster.stats['video_packets_relayed'], 1)
        self.assertEqual(broadcaster.stats['active_video_clients'], 1)
        
        # Test stream removal
        broadcaster.remove_video_stream("client1")
        self.assertEqual(broadcaster.stats['active_video_clients'], 0)
    
    def test_media_relay_integration(self):
        """Test media relay integration."""
        session_manager = SessionManager()
        
        # Mock UDP server
        mock_udp_server = Mock()
        
        # Create media relay
        media_relay = MediaRelay(session_manager, mock_udp_server)
        
        # Test relay initialization
        self.assertIsNotNone(media_relay.audio_mixer)
        self.assertIsNotNone(media_relay.video_broadcaster)
        
        # Test packet processing
        audio_packet = MessageFactory.create_audio_packet("client1", 0, b"audio_data")
        video_packet = MessageFactory.create_video_packet("client1", 0, b"video_data")
        
        # Should not raise exceptions
        media_relay.process_audio_packet(audio_packet, ("127.0.0.1", 8081))
        media_relay.process_video_packet(video_packet, ("127.0.0.1", 8081))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        self.session_manager = SessionManager()
    
    def test_empty_operations(self):
        """Test operations with empty data."""
        # Empty participant list
        participants = self.session_manager.get_participant_list()
        self.assertEqual(len(participants), 0)
        
        # Empty chat history
        chat_history = self.session_manager.get_chat_history()
        self.assertEqual(len(chat_history), 0)
        
        # Empty file list
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 0)
    
    def test_boundary_values(self):
        """Test boundary values."""
        # Maximum username length
        long_username = "a" * 1000
        client_id = self.session_manager.add_client(Mock(), long_username)
        self.assertIsNotNone(client_id)
        
        client = self.session_manager.get_client(client_id)
        self.assertEqual(client.username, long_username)
        
        # Very long message
        long_message = "x" * 10000
        message = MessageFactory.create_chat_message(client_id, long_message)
        self.session_manager.add_chat_message(message)
        
        chat_history = self.session_manager.get_chat_history()
        self.assertEqual(len(chat_history), 1)
        self.assertEqual(chat_history[0].data['message'], long_message)
    
    def test_rapid_operations(self):
        """Test rapid successive operations."""
        # Rapid client add/remove
        for i in range(100):
            client_id = self.session_manager.add_client(Mock(), f"RapidClient{i}")
            self.session_manager.remove_client(client_id)
        
        # Should have no clients left
        participants = self.session_manager.get_participant_list()
        self.assertEqual(len(participants), 0)
        
        # Rapid message sending
        client_id = self.session_manager.add_client(Mock(), "MessageSender")
        
        for i in range(1000):
            message = MessageFactory.create_chat_message(client_id, f"Rapid message {i}")
            self.session_manager.add_chat_message(message)
        
        chat_history = self.session_manager.get_chat_history()
        self.assertEqual(len(chat_history), 1000)
    
    def test_unicode_handling(self):
        """Test Unicode and special character handling."""
        unicode_names = [
            "用户名",  # Chinese
            "пользователь",  # Russian
            "مستخدم",  # Arabic
            "🎮🎯🎲",  # Emojis
            "Ñoño",  # Spanish
            "Müller"  # German
        ]
        
        for name in unicode_names:
            client_id = self.session_manager.add_client(Mock(), name)
            self.assertIsNotNone(client_id)
            
            client = self.session_manager.get_client(client_id)
            self.assertEqual(client.username, name)
            
            # Test Unicode messages
            unicode_message = f"Hello from {name}! 🌍"
            message = MessageFactory.create_chat_message(client_id, unicode_message)
            self.session_manager.add_chat_message(message)
        
        # Verify all messages were stored correctly
        chat_history = self.session_manager.get_chat_history()
        self.assertEqual(len(chat_history), len(unicode_names))


if __name__ == '__main__':
    # Run all tests with detailed output
    unittest.main(verbosity=2, buffer=True)