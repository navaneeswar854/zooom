"""
End-to-end workflow tests for the LAN Collaboration Suite.
Tests complete collaboration workflows with all features integrated.
"""

import unittest
import sys
import os
import threading
import time
import tempfile
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.session_manager import SessionManager
from server.network_handler import NetworkHandler
from client.connection_manager import ConnectionManager
from client.main_client import CollaborationClient
from common.messages import TCPMessage, UDPPacket, MessageType, MessageFactory
from common.file_metadata import FileMetadata, FileValidator


class TestCompleteCollaborationWorkflow(unittest.TestCase):
    """Test complete collaboration workflow from start to finish."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []
        
        # Create test server
        self.session_manager = SessionManager(file_storage_dir=self.temp_dir)
        
        # Mock network components for testing
        self.mock_tcp_socket = Mock()
        self.mock_udp_socket = Mock()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def test_complete_session_lifecycle(self):
        """Test complete session lifecycle from creation to cleanup."""
        # 1. Create session
        session_info = self.session_manager.get_session_info()
        self.assertIsInstance(session_info, dict)
        self.assertEqual(session_info['total_clients'], 0)
        
        # 2. Add clients
        client1_id = self.session_manager.add_client(self.mock_tcp_socket, "Alice")
        client2_id = self.session_manager.add_client(self.mock_tcp_socket, "Bob")
        
        self.assertIsInstance(client1_id, str)
        self.assertIsInstance(client2_id, str)
        self.assertNotEqual(client1_id, client2_id)
        
        # 3. Verify participants
        participants = self.session_manager.get_participant_list()
        self.assertEqual(len(participants), 2)
        
        participant_names = [p['username'] for p in participants]
        self.assertIn("Alice", participant_names)
        self.assertIn("Bob", participant_names)
        
        # 4. Test media status updates
        success = self.session_manager.update_client_media_status(
            client1_id, video_enabled=True, audio_enabled=True
        )
        self.assertTrue(success)
        
        # 5. Test presenter role
        success = self.session_manager.set_presenter(client1_id)
        self.assertTrue(success)
        
        presenter = self.session_manager.get_presenter()
        self.assertIsNotNone(presenter)
        self.assertEqual(presenter.client_id, client1_id)
        
        # 6. Test screen sharing
        success = self.session_manager.start_screen_sharing(client1_id)
        self.assertTrue(success)
        self.assertTrue(self.session_manager.is_screen_sharing_active())
        
        # 7. Test chat messages
        chat_message = MessageFactory.create_chat_message(client1_id, "Hello everyone!")
        self.session_manager.add_chat_message(chat_message)
        
        chat_history = self.session_manager.get_chat_history()
        self.assertGreater(len(chat_history), 0)
        
        # 8. Test client removal
        success = self.session_manager.remove_client(client2_id)
        self.assertTrue(success)
        
        participants = self.session_manager.get_participant_list()
        self.assertEqual(len(participants), 1)
        
        # 9. Final cleanup
        success = self.session_manager.remove_client(client1_id)
        self.assertTrue(success)
        
        final_info = self.session_manager.get_session_info()
        self.assertEqual(final_info['total_clients'], 0)
    
    def test_file_sharing_workflow(self):
        """Test complete file sharing workflow."""
        # 1. Create test file
        test_file_path = Path(self.temp_dir) / "test_document.txt"
        test_content = "This is a test document for file sharing."
        test_file_path.write_text(test_content)
        
        # 2. Validate file
        is_valid, error_msg = FileValidator.validate_file(str(test_file_path))
        self.assertTrue(is_valid, f"File validation failed: {error_msg}")
        
        # 3. Create file metadata
        file_metadata = FileMetadata(
            filename="test_document.txt",
            filesize=len(test_content),
            uploader_id="client1"
        )
        
        # Calculate hash
        file_hash = file_metadata.calculate_hash(str(test_file_path))
        self.assertIsInstance(file_hash, str)
        self.assertEqual(len(file_hash), 64)  # SHA-256 hash length
        
        # 4. Add to session
        success = self.session_manager.add_file_metadata(file_metadata)
        self.assertTrue(success)
        
        # 5. Start upload
        success, error_msg = self.session_manager.start_file_upload(file_metadata)
        self.assertTrue(success, f"Upload start failed: {error_msg}")
        
        # 6. Simulate file upload in chunks
        chunk_size = 1024
        file_data = test_content.encode('utf-8')
        total_chunks = (len(file_data) + chunk_size - 1) // chunk_size
        
        for i in range(total_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(file_data))
            chunk_data = file_data[start_idx:end_idx]
            
            success, error_msg, is_complete = self.session_manager.process_file_chunk(
                file_metadata.file_id, i, total_chunks, chunk_data
            )
            
            self.assertTrue(success, f"Chunk {i} processing failed: {error_msg}")
            
            if i == total_chunks - 1:
                self.assertTrue(is_complete, "Upload should be complete")
        
        # 7. Verify file is available
        shared_files = self.session_manager.get_all_shared_files()
        self.assertEqual(len(shared_files), 1)
        self.assertEqual(shared_files[0].filename, "test_document.txt")
        
        # 8. Get file path and verify integrity
        file_path = self.session_manager.get_file_path(file_metadata.file_id)
        self.assertIsNotNone(file_path)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify hash
        self.assertTrue(file_metadata.verify_hash(file_path))
    
    def test_multi_client_communication(self):
        """Test communication between multiple clients."""
        # Add multiple clients
        clients = {}
        for i, name in enumerate(["Alice", "Bob", "Charlie"]):
            client_id = self.session_manager.add_client(Mock(), name)
            clients[name] = client_id
        
        # Test chat communication
        messages = [
            ("Alice", "Hello everyone!"),
            ("Bob", "Hi Alice!"),
            ("Charlie", "Good morning!"),
            ("Alice", "How is everyone doing?"),
            ("Bob", "Great, thanks for asking!")
        ]
        
        for sender_name, message_text in messages:
            sender_id = clients[sender_name]
            chat_message = MessageFactory.create_chat_message(sender_id, message_text)
            self.session_manager.add_chat_message(chat_message)
        
        # Verify chat history
        chat_history = self.session_manager.get_chat_history()
        self.assertEqual(len(chat_history), len(messages))
        
        # Verify message order and content
        for i, (expected_sender, expected_text) in enumerate(messages):
            message = chat_history[i]
            self.assertEqual(message.data['message'], expected_text)
            self.assertEqual(message.sender_id, clients[expected_sender])
        
        # Test presenter role switching
        # Alice becomes presenter
        success = self.session_manager.set_presenter(clients["Alice"])
        self.assertTrue(success)
        
        presenter = self.session_manager.get_presenter()
        self.assertEqual(presenter.client_id, clients["Alice"])
        
        # Bob requests presenter role (should fail while Alice is presenting)
        success, message = self.session_manager.request_presenter_role(clients["Bob"])
        self.assertFalse(success)
        self.assertIn("already taken", message)
        
        # Alice releases presenter role
        success = self.session_manager.clear_presenter()
        self.assertTrue(success)
        
        # Bob becomes presenter
        success = self.session_manager.set_presenter(clients["Bob"])
        self.assertTrue(success)
        
        presenter = self.session_manager.get_presenter()
        self.assertEqual(presenter.client_id, clients["Bob"])
    
    def test_media_streaming_simulation(self):
        """Test media streaming workflow simulation."""
        # Add clients
        client1_id = self.session_manager.add_client(Mock(), "StreamerAlice")
        client2_id = self.session_manager.add_client(Mock(), "ViewerBob")
        
        # Enable media for client1
        self.session_manager.update_client_media_status(
            client1_id, video_enabled=True, audio_enabled=True
        )
        
        # Set UDP addresses (simulated)
        self.session_manager.update_client_udp_address(client1_id, ("192.168.1.100", 8081))
        self.session_manager.update_client_udp_address(client2_id, ("192.168.1.101", 8081))
        
        # Verify UDP clients
        udp_clients = self.session_manager.get_clients_with_udp()
        self.assertEqual(len(udp_clients), 2)
        
        # Simulate audio packets
        for i in range(5):
            audio_packet = MessageFactory.create_audio_packet(
                sender_id=client1_id,
                sequence_num=i,
                audio_data=b"fake_audio_data_" + str(i).encode()
            )
            
            # Verify packet structure
            self.assertEqual(audio_packet.sender_id, client1_id)
            self.assertEqual(audio_packet.sequence_num, i)
            self.assertIsInstance(audio_packet.data, bytes)
        
        # Simulate video packets
        for i in range(3):
            video_packet = MessageFactory.create_video_packet(
                sender_id=client1_id,
                sequence_num=i,
                video_data=b"fake_video_frame_" + str(i).encode()
            )
            
            # Verify packet structure
            self.assertEqual(video_packet.sender_id, client1_id)
            self.assertEqual(video_packet.sequence_num, i)
            self.assertIsInstance(video_packet.data, bytes)
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        # Test invalid client operations
        invalid_client_id = "nonexistent_client"
        
        # Should fail gracefully
        success = self.session_manager.update_client_media_status(invalid_client_id, video_enabled=True)
        self.assertFalse(success)
        
        success = self.session_manager.set_presenter(invalid_client_id)
        self.assertFalse(success)
        
        client = self.session_manager.get_client(invalid_client_id)
        self.assertIsNone(client)
        
        # Test invalid file operations
        invalid_file_id = "nonexistent_file"
        file_path = self.session_manager.get_file_path(invalid_file_id)
        self.assertIsNone(file_path)
        
        # Test file validation errors
        invalid_file_path = "/nonexistent/path/file.txt"
        is_valid, error_msg = FileValidator.validate_file(invalid_file_path)
        self.assertFalse(is_valid)
        self.assertIn("does not exist", error_msg)
        
        # Test heartbeat timeout simulation
        client_id = self.session_manager.add_client(Mock(), "TestClient")
        
        # Simulate old heartbeat
        client = self.session_manager.get_client(client_id)
        client.last_heartbeat = time.time() - 60  # 60 seconds ago
        
        # Check for inactive clients
        inactive_clients = self.session_manager.get_inactive_clients(timeout_seconds=30)
        self.assertIn(client_id, inactive_clients)
        
        # Cleanup inactive clients
        removed_clients = self.session_manager.cleanup_inactive_clients(timeout_seconds=30)
        self.assertIn(client_id, removed_clients)
        
        # Verify client was removed
        client = self.session_manager.get_client(client_id)
        self.assertIsNone(client)
    
    def test_concurrent_operations(self):
        """Test concurrent operations in the session."""
        results = {}
        errors = []
        
        def add_clients():
            try:
                for i in range(5):
                    client_id = self.session_manager.add_client(Mock(), f"Client{i}")
                    results[f"client_{i}"] = client_id
            except Exception as e:
                errors.append(f"add_clients: {e}")
        
        def send_messages():
            try:
                # Wait for clients to be added
                time.sleep(0.1)
                for i in range(10):
                    if f"client_0" in results:
                        message = MessageFactory.create_chat_message(
                            results["client_0"], f"Message {i}"
                        )
                        self.session_manager.add_chat_message(message)
            except Exception as e:
                errors.append(f"send_messages: {e}")
        
        def update_media_status():
            try:
                # Wait for clients to be added
                time.sleep(0.1)
                for i in range(5):
                    if f"client_{i}" in results:
                        self.session_manager.update_client_media_status(
                            results[f"client_{i}"], 
                            video_enabled=(i % 2 == 0),
                            audio_enabled=True
                        )
            except Exception as e:
                errors.append(f"update_media_status: {e}")
        
        # Run operations concurrently
        threads = [
            threading.Thread(target=add_clients),
            threading.Thread(target=send_messages),
            threading.Thread(target=update_media_status)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        # Check for errors
        if errors:
            self.fail(f"Concurrent operations failed: {errors}")
        
        # Verify results
        self.assertEqual(len(results), 5)  # 5 clients added
        
        chat_history = self.session_manager.get_chat_history()
        self.assertGreaterEqual(len(chat_history), 10)  # At least 10 messages
        
        participants = self.session_manager.get_participant_list()
        self.assertEqual(len(participants), 5)  # 5 participants


class TestSystemIntegration(unittest.TestCase):
    """Test system integration scenarios."""
    
    def test_message_serialization_roundtrip(self):
        """Test message serialization and deserialization."""
        # Test TCP message
        original_tcp = MessageFactory.create_chat_message("client1", "Hello World!")
        serialized_tcp = original_tcp.serialize()
        deserialized_tcp = TCPMessage.deserialize(serialized_tcp)
        
        self.assertEqual(original_tcp.msg_type, deserialized_tcp.msg_type)
        self.assertEqual(original_tcp.sender_id, deserialized_tcp.sender_id)
        self.assertEqual(original_tcp.data, deserialized_tcp.data)
        
        # Test UDP packet
        original_udp = MessageFactory.create_audio_packet("client1", 42, b"audio_data")
        serialized_udp = original_udp.serialize()
        deserialized_udp = UDPPacket.deserialize(serialized_udp)
        
        self.assertEqual(original_udp.packet_type, deserialized_udp.packet_type)
        self.assertEqual(original_udp.sender_id, deserialized_udp.sender_id)
        self.assertEqual(original_udp.sequence_num, deserialized_udp.sequence_num)
        self.assertEqual(original_udp.data, deserialized_udp.data)
    
    def test_file_metadata_operations(self):
        """Test file metadata operations."""
        # Create test file
        temp_dir = tempfile.mkdtemp()
        test_file = Path(temp_dir) / "test.txt"
        test_content = "Test file content for metadata testing"
        test_file.write_text(test_content)
        
        try:
            # Create metadata
            metadata = FileMetadata(
                filename="test.txt",
                filesize=len(test_content),
                uploader_id="test_user"
            )
            
            # Test validation
            self.assertTrue(metadata.is_valid())
            
            # Test hash calculation
            file_hash = metadata.calculate_hash(str(test_file))
            self.assertIsInstance(file_hash, str)
            self.assertEqual(len(file_hash), 64)
            
            # Test hash verification
            self.assertTrue(metadata.verify_hash(str(test_file)))
            
            # Test serialization
            metadata_dict = metadata.to_dict()
            restored_metadata = FileMetadata.from_dict(metadata_dict)
            
            self.assertEqual(metadata.filename, restored_metadata.filename)
            self.assertEqual(metadata.filesize, restored_metadata.filesize)
            self.assertEqual(metadata.uploader_id, restored_metadata.uploader_id)
            
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_performance_under_load(self):
        """Test system performance under simulated load."""
        session_manager = SessionManager()
        
        # Add many clients
        client_ids = []
        start_time = time.time()
        
        for i in range(50):
            client_id = session_manager.add_client(Mock(), f"LoadTestClient{i}")
            client_ids.append(client_id)
        
        client_creation_time = time.time() - start_time
        
        # Send many messages
        start_time = time.time()
        
        for i in range(100):
            sender_id = client_ids[i % len(client_ids)]
            message = MessageFactory.create_chat_message(sender_id, f"Load test message {i}")
            session_manager.add_chat_message(message)
        
        message_processing_time = time.time() - start_time
        
        # Verify performance is reasonable
        self.assertLess(client_creation_time, 5.0, "Client creation took too long")
        self.assertLess(message_processing_time, 2.0, "Message processing took too long")
        
        # Verify data integrity
        participants = session_manager.get_participant_list()
        self.assertEqual(len(participants), 50)
        
        chat_history = session_manager.get_chat_history()
        self.assertEqual(len(chat_history), 100)


if __name__ == '__main__':
    # Configure test runner for comprehensive output
    unittest.main(verbosity=2, buffer=True)